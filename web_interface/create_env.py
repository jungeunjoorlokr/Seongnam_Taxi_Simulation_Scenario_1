def create_env_file():
    env_content = """# OpenAI API 키
OPENAI_API_KEY=your-api-key-here

# 시뮬레이션 경로
SIMULATION_PATH=/Users/jung-eunjoo/Desktop/DTUMOS-Disabled-CallTaxi/visualization/simulation
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print(".env 파일이 생성되었습니다.")
        print("생성된 .env 파일을 열어서 OPENAI_API_KEY 값을 실제 API 키로 수정해주세요.")
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    create_env_file()
