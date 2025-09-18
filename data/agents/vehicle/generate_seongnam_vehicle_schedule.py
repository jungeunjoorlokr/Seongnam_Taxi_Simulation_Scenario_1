"""
성남 차량 스케줄/초기위치 생성 스크립트 (단발성)
- 주어진 성남 경계 내에서 초기 위치 랜덤 배치
- corp/priv 분할 비율과 교대 스플릿으로 스케줄 생성
- 결과를 CSV로 저장 (기본: data/agents/vehicle/vehicle_data.csv)
"""

import argparse
import random
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon

# -------- 사용자 정의 기본값 --------
DEFAULT_BOUNDARY = "data/etc/seongnam_boundary.geojson"
DEFAULT_OUTPUT   = "data/agents/vehicle/vehicle_data.csv"

# 스케줄 스플릿 예시 (비율은 합이 1)
# 자정 넘는 경우 +24 처리 (4시 → 28시)
#(근무 시작 시각, 근무 종료 시각, 해당 패턴 비율)
DEFAULT_CORP_SPLITS = [("20","28",0.60), ("14","24",0.25), ("22","26",0.15)]  # 법인(1)
DEFAULT_PRIV_SPLITS = [("18","26",0.70), ("22","27",0.30)]                     # 개인(0)

def convert_schedule_time(start_str, end_str):
    """자정 넘는 스케줄 처리: 종료 시간이 시작보다 작으면 +24"""
    start = int(start_str)
    end = int(end_str)
    
    # 자정 넘는 경우 (예: 20시~4시)
    if end <= start:
        end += 24  # 4 → 28
    
    return start, end

def build_rows(start_id: int, taxi_type: int, total: int, splits):
    """스케줄 행 생성: (vehicle_id, taxi_type, work_start(h), work_end(h), temporary_stopTime, lat, lon, cartype)"""
    counts = [int(round(total * p)) for _, _, p in splits]
    # 반올림 오차 보정
    diff = total - sum(counts)
    if counts:
        counts[0] += diff

    rows, cur = [], start_id
    for (ws, we, _), cnt in zip(splits, counts):
        # 자정 넘는 시간 변환
        start_h, end_h = convert_schedule_time(ws, we)
        for _ in range(cnt):
            rows.append((cur, taxi_type, start_h, end_h, 0, np.nan, np.nan, 0))
            cur += 1
    return rows, cur

def random_point_in_polygon(polygon: Polygon) -> Point:
    """다각형 내부 임의 점 하나 뽑기"""
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(p):
            return p

def assign_random_points(df: pd.DataFrame, union_poly):
    """Geo 경계(union_poly) 내부에서 차량 초기 lat/lon 부여"""
    points = []
    for _ in range(len(df)):
        if isinstance(union_poly, (Polygon, MultiPolygon)):
            poly = random.choice(list(union_poly.geoms)) if isinstance(union_poly, MultiPolygon) else union_poly
            pt = random_point_in_polygon(poly)
            points.append((pt.y, pt.x))  # (lat, lon)
        else:
            points.append((np.nan, np.nan))
    df["lat"] = [p[0] for p in points]
    df["lon"] = [p[1] for p in points]
    return df

def generate_schedule(n_corp: int, n_priv: int, corp_splits, priv_splits):
    """법인/개인 스케줄 생성 후 결합"""
    rows1, next_id = build_rows(0, 1, n_corp, corp_splits)  # taxi_type=1(법인)
    rows2, _       = build_rows(next_id, 0, n_priv, priv_splits)  # taxi_type=0(개인)
    vehicle_schedule = pd.DataFrame(
        rows1 + rows2,
        columns=["vehicle_id","taxi_type","work_start","work_end","temporary_stopTime","lat","lon","cartype"]
    )
    return vehicle_schedule

def main():
    ap = argparse.ArgumentParser(description="성남 차량 스케줄/초기위치 생성")
    ap.add_argument("--boundary", default=DEFAULT_BOUNDARY, help="성남 경계 geojson 경로")
    ap.add_argument("--output",   default=DEFAULT_OUTPUT,   help="출력 CSV 경로")
    ap.add_argument("--n-corp",   type=int, default=540,    help="법인 택시 대수")
    ap.add_argument("--n-priv",   type=int, default=440,    help="개인 택시 대수")
    ap.add_argument("--seed",     type=int, default=42,     help="난수 시드")
    ap.add_argument("--overwrite", action="store_true",     help="기존 파일 덮어쓰기 허용")
    
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    # 1) 스케줄 생성
    vehicle_schedule = generate_schedule(
        n_corp=args.n_corp,
        n_priv=args.n_priv,
        corp_splits=DEFAULT_CORP_SPLITS,
        priv_splits=DEFAULT_PRIV_SPLITS
    )

    # 2) 경계 로드 및 초기 위치 부여
    gdf = gpd.read_file(args.boundary)
    union_poly = gdf.unary_union
    vehicle_schedule = assign_random_points(vehicle_schedule, union_poly)

    # 3) 검증 로그
    print("\n생성된 차량 데이터:")
    print(vehicle_schedule.head(10))
    print("\n택시 타입별 분포:")
    print(vehicle_schedule["taxi_type"].value_counts())
    print(f"\n총 차량수: {len(vehicle_schedule)}")
    print(f"\n스케줄 시간 범위:")
    print(f"  work_start: {vehicle_schedule['work_start'].min()}시 ~ {vehicle_schedule['work_start'].max()}시")
    print(f"  work_end: {vehicle_schedule['work_end'].min()}시 ~ {vehicle_schedule['work_end'].max()}시")
    
    # 자정 넘는 차량 체크
    midnight_cross = vehicle_schedule[vehicle_schedule['work_end'] > 24]
    if len(midnight_cross) > 0:
        print(f"\n자정 넘는 차량: {len(midnight_cross)}대")
        print(midnight_cross[['vehicle_id', 'work_start', 'work_end']].head())

    # 4) 저장 (기존 파일 보호)
    import os
    if os.path.exists(args.output) and not args.overwrite:
        raise FileExistsError(f"이미 파일이 있습니다: {args.output} (덮어쓰려면 --overwrite)")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    vehicle_schedule.to_csv(args.output, index=False, encoding="utf-8")
    print(f"\n저장 완료: {args.output}")

if __name__ == "__main__":
    main()