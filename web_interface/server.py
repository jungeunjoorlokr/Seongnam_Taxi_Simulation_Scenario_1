########################################################
#Server
########################################################
# 시작 명령어: python3.13 web_interface/server.py
#library
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import re
import json
import subprocess
import os
import time
import webcolors
import openai
from langchain_community.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from fastapi.staticfiles import StaticFiles
import threading




########################################################
#Load environment variables
########################################################

# .env 파일 로드
load_dotenv()

########################################################
#OpenAI API 키를 환경변수에서 가져오기
########################################################

openai.api_key = os.getenv('OPENAI_API_KEY')

########################################################
#Kill process on port
########################################################
# 서버 시작 전에 8090 포트 확인 및 정리
def kill_process_on_port(port):
    try:
        # lsof 명령어로 포트 사용 중인 프로세스 확인
        process = subprocess.Popen(
            f"lsof -t -i:{port}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        pid, err = process.communicate()
        
        if pid:
            # 프로세스 종료
            subprocess.run(f"kill -9 {pid}", shell=True)
            print(f"포트 {port}의 프로세스 종료됨")
            time.sleep(1)  # 프로세스가 완전히 종료되기를 기다림
            return True
    except Exception as e:
        print(f"프로세스 종료 중 오류: {str(e)}")
    return False

kill_process_on_port(8090)

########################################################
#FastAPI
########################################################

app = FastAPI()
simulation_running = False

# 시뮬레이션 상태 초기화
simulation_status = {
    "running": False,
    "progress": 0,
    "message": "대기 중",
    "estimated_time": 0
}

app.mount("/image", StaticFiles(directory="web_interface/public/image"), name="image")
app.mount("/dashboard", StaticFiles(directory="visualization/dashboard"), name="dashboard")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 설정
app.mount("/static", StaticFiles(directory="web_interface"), name="static")
# 시뮬레이션 경로 설정
SIMULATION_PATH = "../scenario_seongnam_general_dispatch/visualization/simulation"
TRIP_JS_PATH = os.path.join(SIMULATION_PATH, "src/components/Trip.js")
# 시뮬레이션 결과 파일 경로 설정
RESULT_JSON_PATH = os.path.join(SIMULATION_PATH, "public/data/result.json")
# Trip.js 파일 경로 확인을 위한 전체 경로 출력
trip_js_path = os.path.join(SIMULATION_PATH, "src/components/Trip.js")
print(f"Trip.js 파일 경로: {trip_js_path}")

########################################################
#Load prompt
########################################################

# 외부 프롬프트 텍스트 불러오기 함수
def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
# 시각화 속성 정의 불러오기
def load_visualization_schema(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

VISUALIZATION_SCHEMA = load_visualization_schema(
    "./web_interface/visualization_schema.txt"
)

########################################################
#Load color map
########################################################

# 기본 색상 매핑
COLOR_MAP = {
    "빨간": [255, 0, 0],
    "빨강": [255, 0, 0],
    "빨": [255, 0, 0],
    "파란": [0, 0, 255],
    "파랑": [0, 0, 255],
    "파": [0, 0, 255],
    "초록": [0, 255, 0],
    "초": [0, 255, 0],
    "노란": [255, 255, 0],
    "노랑": [255, 255, 0],
    "보라": [128, 0, 128],
    "분홍": [255, 192, 203],
    "핑크": [255, 192, 203],
    "핑": [255, 192, 203],
    "주황": [255, 165, 0],
    "검정": [0, 0, 0],
    "검": [0, 0, 0],
    "하늘": [135, 206, 235],
}

########################################################
#Load trail map
########################################################

# 궤적 길이 매핑
TRAIL_MAP = {
    "짧게": 0.2,
    "보통길이": 0.5,
    "길게": 0.8,
    "매우길게": 1.0
}

########################################################
#LLM
########################################################

# LLM 설정
llm = OpenAI(temperature=0.3)

# 요청 유형 분류를 위한 프롬프트
intent_prompt = PromptTemplate(
    input_variables=["command"],
    template=load_prompt("web_interface/prompt/intent_prompt.txt")
)

########################################################
#Load prompt
########################################################

# 상태 확인 프롬프트update_visualization_settings
status_prompt = PromptTemplate(
    input_variables=["file_content", "command"],
    template=load_prompt("web_interface/prompt/status_prompt.txt")
)

# 🔁 PromptTemplate 내부 중괄호 오류 방지를 위한 안전한 생성 함수
def safe_prompt_template(raw_template: str, variables: list):
    safe = raw_template.replace("{", "{{").replace("}", "}}")
    for var in variables:
        safe = safe.replace(f"{{{{{var}}}}}", f"{{{var}}}")
    return safe

#상태 변경 프롬프트
change_prompt = PromptTemplate(
    input_variables=["command", "visualization_schema"],
    template=safe_prompt_template(
        load_prompt("web_interface/prompt/change_prompt.txt"),
        ["command", "visualization_schema"]
    )
)

# 일반 대화 프롬프트
general_prompt = PromptTemplate(
    input_variables=["command"],
    template=load_prompt("web_interface/prompt/general_prompt.txt")
)

# 시뮬레이션 조정 프롬프트
simulation_adjust_prompt = PromptTemplate(
    input_variables=["command"],
    template=safe_prompt_template(
        load_prompt("web_interface/prompt/simulation_adjust_prompt.txt"),
        ["command"]
    )
)

# 시뮬레이션 실행 프롬프트
simulation_run_prompt = PromptTemplate(
    input_variables=["command"],
    template=load_prompt("web_interface/prompt/simulation_run_prompt.txt")
)


########################################################
#Load chain
########################################################

# 체인 생성
intent_chain = LLMChain(llm=llm, prompt=intent_prompt)
status_chain = LLMChain(llm=llm, prompt=status_prompt)
change_chain = LLMChain(llm=llm, prompt=change_prompt)
general_chain = LLMChain(llm=llm, prompt=general_prompt)
simulation_adjust_chain = LLMChain(llm=llm, prompt=simulation_adjust_prompt)
simulation_run_chain = LLMChain(llm=llm, prompt=simulation_run_prompt)

########################################################
#Update visualization settings
########################################################

def update_visualization_settings(analysis_result):
    try:
        with open(TRIP_JS_PATH, 'r') as file:
            content = file.read()

        target_layer = analysis_result['target_layer']
        property_name = analysis_result['property']
        value = analysis_result['value']

        #기존 -> layer_pattern = rf'id:\s*["\']{target_layer}["\'],[\s\S]*?new [\w]+Layer\('

        # layer_pattern = rf'new [\w]+Layer\(\{{[\s\S]*?id:\s*["\']{target_layer}["\']'
        layer_pattern = rf'new [\w]+Layer\(\{{[^{{}}]*?id:\s*["\']{target_layer}["\'][^{{}}]*?\}}\)'
        # layer_pattern = rf'new [\w]+Layer\(\{{[\s\S]*?id:\s*["\']{target_layer}["\'][\s\S]*?\}}\)'
        # 🔍 여기서 디버깅 출력 추가
        print("===== 정규식 레이어 찾기 =====")
        print(f"target_layer: {target_layer}")
        print(f"정규식: {layer_pattern}")

        # 정확히 getColor: [...]만 대체하도록
        # 먼저 해당 레이어 블록만 추출
        
        layer_match = re.search(layer_pattern, content)
        if not layer_match:
            raise Exception("대상 레이어를 Trip.js에서 찾을 수 없습니다.")

        layer_block = layer_match.group()

        if property_name == "getColor" and isinstance(value, list):
            color_func_pattern = r'getColor\s*:\s*d\s*=>\s*d\.board\s*===\s*1\s*\?\s*(\[[^\]]+\])\s*:\s*(\[[^\]]+\])'
            match = re.search(color_func_pattern, layer_block)
            if not match:
                raise Exception("getColor 함수 형태를 찾을 수 없습니다.")

            boarding_color = match.group(1)
            empty_color = match.group(2)

            target = analysis_result.get("target")  # "boarding" 또는 "empty"

            if target == "boarding":
                new_func = f"getColor: d => d.board === 1 ? [{', '.join(map(str, value))}] : {empty_color}"
            elif target == "empty":
                new_func = f"getColor: d => d.board === 1 ? {boarding_color} : [{', '.join(map(str, value))}]"
            else:
                raise Exception("analysis_result에 'target' 필드가 없거나 값이 잘못되었습니다 (boarding/empty 중 하나여야 함)")

            updated_block = re.sub(color_func_pattern, new_func, layer_block)

        # 전체 content에 대체
        new_content = content.replace(layer_block, updated_block)

        with open(TRIP_JS_PATH, 'w') as file:
            file.write(new_content)

        return True

    except Exception as e:
        raise Exception(f"시각화 설정 업데이트 실패: {str(e)}")

########################################################
#Load index
########################################################

@app.get("/")
async def read_index():
    return FileResponse("web_interface/index.html")
########################################################
#Process command
########################################################

@app.post("/process-command")
async def process_command(request: Request):
    data = await request.json()
    command = data.get("command", "")
    
    try:
        # 시뮬레이션 시작 명령 처리
        if "시뮬레이션 시작" in command:
            return await start_simulation()
        
        # 명령어 의도 분석
        intent_result = json.loads(intent_chain.run(command=command))
        intent_type = intent_result['type']
        print(f"intent_type: {intent_type}")
        
        if "평균 대기" in command or "대기 시간" in command:
            # (1) 현재 시간
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            
            # (2) result.json 파일 읽기
            try:
                df_result = pd.read_json(RESULT_JSON_PATH)
                latest_record = df_result.iloc[-1]  # 가장 마지막 값 사용
                average_waiting_time = latest_record['average_waiting_time']
            except Exception as e:
                average_waiting_time = 0  # 읽기 실패 시 0 처리
            
            # (3) 자연어 응답 구성
            result_message = f"현재 {hour}시 {minute}분 기준 평균 대기 시간은 약 {average_waiting_time:.1f}분입니다."

            return {
                "status": "success",
                "message": result_message
            }
            
        elif intent_type == "STATE_CHANGE":
            # 상태 변경 명령 처리
            change_result = change_chain.run(command=command)
            print(f"Change chain 응답: {change_result}")  # 디버깅 로그

            # JSON 객체만 추출 (중괄호 두 겹 또는 한 겹 모두 지원)
            match = re.search(r'\{[^{]*"target_layer"\s*:\s*"[^"]+".*?\}', change_result, re.DOTALL)
            if not match:
                raise Exception("JSON 형식의 응답을 찾지 못했습니다")

            try:
                json_str = match.group(0)  # 전체 JSON 문자열 통째로
                analysis = json.loads(json_str)

                # 필수 키 확인
                required_keys = ['target_layer', 'property', 'value', 'explanation']
                if not all(key in analysis for key in required_keys):
                    raise Exception("응답에 필수 키가 누락되었습니다")

                # 시각화 설정 업데이트
                update_visualization_settings(analysis)

                message = "=== 명령어 분석 결과 ===\n\n"
                message += f"1. 변경 대상: {analysis['target_layer']}\n\n"
                message += f"2. 변경 속성: {analysis['property']}\n\n"
                message += f"3. 변경 값: {analysis['value']}\n\n"
                message += f"4. 변경 이유: {analysis['explanation']}"

                return {
                    "status": "success",
                    "intent_type": intent_type,
                    "message": message
                }
            

            except json.JSONDecodeError as e:
                print(f"JSON 파싱 오류. 원본 응답: {change_result}")
                raise Exception(f"명령어 분석 결과를 처리할 수 없습니다: {str(e)}")
            except Exception as e:
                raise Exception(f"명령어 처리 중 오류 발생: {str(e)}")
            
        elif intent_type == "STATUS_CHECK":
            try:
                # 파일이 최신 상태로 디스크에 기록될 수 있도록 약간의 지연
                time.sleep(0.3)

                # 🔁 Trip.js 파일을 강제로 다시 읽음
                with open(TRIP_JS_PATH, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    print(f"file_content: {file_content}")

                # 🔍 상태 체크 체인 실행
                result = status_chain.run(file_content=file_content, command=command)

                return {
                    "status": "success",
                    "intent_type": intent_type,
                    "message": result
                }
            
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"STATUS_CHECK 처리 실패: {str(e)}"
                }
        elif intent_type == "SET_VALUE":
            adjust_result = simulation_adjust_chain.run(command=command)
            print("🔥 command 전달:", command)
            print("📦 adjust_result (원형):", repr(adjust_result))

            try:
                # JSON만 추출
                match = re.search(r'\{.*\}', adjust_result, re.DOTALL)
                if not match:
                    raise Exception("JSON 객체를 추출할 수 없습니다.")
                adjust_json = json.loads(match.group(0))

                if adjust_json.get("target_variable") == "num_taxis":
                    taxi_num = adjust_json.get("value")
                    success, msg = modify_taxi_number_in_main_file(taxi_num)
                    if success:
                        return {
                            "status": "success",
                            "intent_type": intent_type,
                            "message": msg
                        }
                    else:
                        raise Exception(msg)
                else:
                    raise Exception("target_variable이 'num_taxis'가 아님")
            except Exception as e:
                return {
                    "status": "error",
                    "intent_type": intent_type,
                    "message": f"SET_VALUE 처리 중 오류 발생: {str(e)}"
        }

        elif intent_type == "START_SIMULATION":
            global simulation_running, simulation_status  # ✅ 전역 변수 사용

            if simulation_running:
                return {
                    "status": "error",
                    "intent_type": intent_type,
                    "message": "⚠️ 시뮬레이션이 이미 실행 중입니다. 잠시 후 다시 시도해주세요."
                }

            try:
                simulation_running = True  # ✅ 실행 시작 표시

                simulation_status = {
                    "running": True,
                    "progress": 0,
                    "message": "🚦 시뮬레이션 시작 중...",
                    "estimated_time": 300  # 5분 예상
                }

                simulation_run_result = simulation_run_chain.run(command=command)
                print("🧠 simulation_run_result:", repr(simulation_run_result))

                proc = subprocess.Popen(
                    ["python3.13", "../scenario_seongnam_general_dispatch/main.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
    
                def capture_output():  # 🟢 여기!!!
                    with open('simulation_output.txt', 'w', encoding='utf-8') as f:
                        for line in proc.stdout:
                            # 터미널에도 출력 (디버깅용)
                            print(f"📤 {line}", end='')  # 🟢 이미 있네요!
                            
                            # 파일에 바로 쓰기
                            f.write(line)
                            f.flush()
                
                thread = threading.Thread(target=capture_output)
                thread.daemon = True
                thread.start()
                return {
                    "status": "success",
                    "intent_type": intent_type,
                    "message": "🚦 시뮬레이션이 시작되었습니다. 진행 상황을 확인 중..."
                }
                
                # ❌ 아래 코드는 실행 안 됨 (return 후라서)
                # 이 부분은 나중에 다른 방법으로 처리해야 함
                
            except Exception as e:
                simulation_running = False
                return {
                    "status": "error",
                    "intent_type": intent_type,
                    "message": f"main.py 실행 실패: {str(e)}"
                }
                
        else:  # GENERAL
            # 일반 대화 처리
            result = general_chain.run(command=command)
            return {
                "status": "success",
                "intent_type": intent_type, 
                "message": result
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"오류: {str(e)}"
        }

########################################################
#Get trip colors
########################################################

@app.get("/get-trip-colors")
async def get_trip_colors():
    try:
        with open(TRIP_JS_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # getColor 함수에서 색상 추출
        match = re.search(r'getColor\s*:\s*d\s*=>\s*d\.board\s*===\s*1\s*\?\s*\[([^\]]+)\]\s*:\s*\[([^\]]+)\]', content)
        if not match:
            raise Exception("getColor 함수에서 색상 정보를 찾을 수 없습니다.")

        boarding = [int(x.strip()) for x in match.group(1).split(',')]
        empty = [int(x.strip()) for x in match.group(2).split(',')]

        return {
            "status": "success",
            "boardingRGB": boarding,
            "emptyRGB": empty
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Trip.js 색상 추출 실패: {str(e)}"
        }

########################################################
#Get simulation status
########################################################

@app.get("/simulation-status")
async def get_simulation_status():
    """시뮬레이션 진행 상태 조회"""
    global simulation_status
    
    # simulation_status.json 파일에서 상태 읽기
    try:
        status_file = "simulation_status.json"
        print(f"📁 상태 파일 경로: {status_file}")

        if os.path.exists(status_file):
            with open(status_file, 'r', encoding='utf-8') as f:
                file_status = json.load(f)
                simulation_status.update(file_status)
                print(f"✅ 상태 읽기 성공: {file_status}")
        else:
            print("❌ 파일이 없습니다!")
    except Exception as e:
        print(f"상태 파일 읽기 실패: {e}")
    
    return simulation_status


########################################################
#Set taxi number
########################################################

# 내부 호출용: 택시 수 설정 로직만 따로 함수로 분리
def modify_taxi_number_in_main_file(new_num):
    try:
        main_path = "../scenario_seongnam_general_dispatch/main.py"
        with open(main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            if line.strip().startswith("num_taxis ="):
                new_lines.append(f"num_taxis = {new_num}  # ← 자연어 명령으로 변경됨\n")
            else:
                new_lines.append(line)

        with open(main_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return True, f"main.py 파일 내 택시 수가 {new_num}대로 설정되었습니다."
    except Exception as e:
        return False, str(e)
    
@app.post("/set-taxi-number")
async def set_taxi_number(request: Request):
    data = await request.json()
    new_num = data.get("num_taxis", 1623)

    try:
        # main.py 파일 열기
        main_path = "../scenario_seongnam_general_dispatch/main.py"
        with open(main_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # num_taxis 줄 찾아서 수정
        new_lines = []
        for line in lines:
            if line.strip().startswith("num_taxis ="):
                new_lines.append(f"num_taxis = {new_num}  # ← 자연어 명령으로 변경됨\n")
            else:
                new_lines.append(line)

        # 다시 파일에 저장
        with open(main_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        return {
            "status": "success",
            "message": f"main.py 파일 내 택시 수가 {new_num}대로 설정되었습니다."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"num_taxis 수정 실패: {str(e)}"
        }
    

########################################################
#Start simulation
########################################################

@app.post("/start-simulation")
async def start_simulation():
    try:
        # React 포트(3000) 정리
        subprocess.run("lsof -t -i:3000 | xargs kill -9", shell=True)
        time.sleep(1)
        
        # 시뮬레이션 시작
        process = subprocess.Popen(
            "npm start",
            shell=True,
            cwd=SIMULATION_PATH
        )
        
        return {
            "status": "success",
            "message": "시뮬레이션이 시작되었습니다. 새 창이 열릴 때까지 기다려주세요."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"시뮬레이션 시작 실패: {str(e)}"
        }

########################################################
#Run server
########################################################


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)