from dotenv import load_dotenv
import os
# test_orchestrator.py
# .env 파일 로드 (가장 먼저 실행해야 함)
load_dotenv(dotenv_path="web_interface/.env")
print("OPENAI_API_KEY loaded?", bool(os.getenv("OPENAI_API_KEY")))

from web_interface.graph.orchestration import invoke




def main():
    print("=== RUN_SIM 테스트 ===")
    result1 = invoke("택시 100대로 시뮬레이션 돌려줘")
    print(result1, "\n")

    print("=== EDIT_CONFIG 테스트 ===")
    result2 = invoke("택시 수를 850대로 바꿔")
    print(result2, "\n")

    print("=== UPDATE_VIZ 테스트 ===")
    result3 = invoke("시각화에서 경로 선을 두껍게 해줘")
    print(result3, "\n")

    print("=== UNKNOWN 테스트 ===")
    result4 = invoke("오늘 점심 뭐먹지?")
    print(result4, "\n")

if __name__ == "__main__":
    main()