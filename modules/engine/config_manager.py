### base configs (기본값 템플릿)
base_configs = {
                'target_region': None,             # 시뮬레이션 대상 지역 이름 (예: '성남 대한민국')
                'problem': 'default',              # 문제 유형 (예: 'default')
                'relocation_region': None,         # 재배치 지역 키 (예: 'seongnam')
                'path': None,                      # 결과 저장 경로 (simul_result 내부)
                'additional_path': None,           # 시나리오별 추가 경로
                'time_range': [0, 1440],           # 시뮬레이션 시간 범위 (분 단위, 0~1440)
                'fail_time': 10,                   # 승객 실패 처리 기준 시간 (분)
                'add_board_time': 0.2,             # 승차 추가 시간 (분, 기본=0.2)
                'add_disembark_time': 0.2,         # 하차 추가 시간 (분, 기본=0.2)
                'matrix_mode': 'street_distance',  # 거리 계산 방식 ['street_distance', 'ETA', 'haversine_distance']
                'dispatch_mode': 'in_order',       # 배차 모드 ['optimization', 'in_order']
                'eta_model': None,                 # ETA 예측 모델 (없으면 None)
                'corp_priv_split': (0.55, 0.45),   # 법인:개인 비율 (기본=55:45)
                'filter_out_of_region': False,     # 지역 경계 밖 데이터 제거 여부
                'view_operation_graph': True       # 운행 그래프 출력 여부
                
                }
# - extract_selector
def extract_selector(service_type):
    from modules.preprocess.data_preprocessor import extract_main
    # service_type = service_type.upper()
    # if service_type == 'DISABLEDCALLTAXI':
    return extract_main


# - dispatch_selector
def dispatch_selector(service_type):
    from modules.dispatch.dispatch_flow import dispatch_main
    # service_type = service_type.upper()
    # if service_type == 'DISABLEDCALLTAXI':    
    return dispatch_main