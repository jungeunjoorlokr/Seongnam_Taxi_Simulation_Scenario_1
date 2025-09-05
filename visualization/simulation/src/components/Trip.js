import React, { useState, useEffect } from 'react';
import { Map } from 'react-map-gl';
import {AmbientLight, PointLight, LightingEffect} from '@deck.gl/core';
import { TripsLayer } from '@deck.gl/geo-layers';
import { ScatterplotLayer, IconLayer } from '@deck.gl/layers';
import ICON_PNG from '../image/icon-atlas.png';
import DeckGL from '@deck.gl/react';
import '../css/trip.css';

const ambientLight = new AmbientLight({
  color: [255, 255, 255],
  intensity: 1.0
});
  
const pointLight = new PointLight({
  color: [255, 255, 255],
  intensity: 2.0,
  position: [-74.05, 40.7, 8000]
});

const lightingEffect = new LightingEffect({ambientLight, pointLight});

const material = {
  ambient: 0.1,
  diffuse: 0.6,
  shininess: 32,
  specularColor: [60, 64, 70]
};

const DEFAULT_THEME = {
  trailColor0: [253, 128, 93],
  trailColor1: [23, 184, 190],
  material,
  effects: [lightingEffect]
};

const INITIAL_VIEW_STATE = {
  longitude: 127.12,
  latitude: 37.42,
  zoom: 11,
  minZoom: 2,
  maxZoom: 20,
  pitch: 0,
  bearing: 0
};

const mapStyle = 'mapbox://styles/spear5306/ckzcz5m8w002814o2coz02sjc';
const MAPBOX_TOKEN = `pk.eyJ1Ijoic3BlYXI1MzA2IiwiYSI6ImNremN5Z2FrOTI0ZGgycm45Mzh3dDV6OWQifQ.kXGWHPRjnVAEHgVgLzXn2g`; 

const currData = (data, time) => {
  const arr = [];
  data.forEach(v => {
    const [start, end] = v.timestamp;
    if ((start <= time) & (time <= end)) {
      arr.push(v.location);
    };
  });
  return arr;
}

const currResult = (data, time) => {
  const result = data.find(v => Number(v.time) === Math.floor(time));
  return result;
}


const ICON_MAPPING = {
  marker: {x: 0, y: 0, width: 128, height: 128, mask: true}
};

const Trip = (props) => {
  const animationSpeed = 5;
  const time = props.time;
  const minTime = props.minTime;
  const maxTime = props.maxTime;

  const DRIVER = props.data.DRIVER_TRIP || [];
  const D_MARKER = currData(props.data.DRIVER_MARKER, time) || [];
  const P_MARKER = currData(props.data.PASSENGER_MARKER, time) || [];

  const CURRENT_RESULT = currResult(props.data.RESULT, time) || {};

  const [animationFrame, setAnimationFrame] = useState('');

  const animate = () => {
    props.setTime(time => {
      if (time > maxTime) {
        return minTime;
      } else {
        return time + (0.01) * animationSpeed;
      };
    });
    const af = window.requestAnimationFrame(animate);
    setAnimationFrame(af);
  };

  useEffect(() => {
    animate();
    return () => window.cancelAnimationFrame(animationFrame);
  }, []);

// 데이터 로드 확인
  useEffect(() => {
    console.log('👀 DRIVER 전체:', DRIVER);
    console.log('👀 DRIVER 타입:', typeof DRIVER);
    console.log('👀 DRIVER는 배열인가?:', Array.isArray(DRIVER));
    
    if (DRIVER && DRIVER.length > 0) {
      console.log('👀 첫 번째 데이터:', DRIVER[0]);
      console.log('👀 trip 데이터:', DRIVER[0]?.trip);
      console.log('👀 timestamp 데이터:', DRIVER[0]?.timestamp);
    }
  }, [DRIVER]);

  
  const layers = [
    // 운전자 경로를 시각화하는 레이어
    new TripsLayer({
      id: 'DRIVER', // 레이어의 고유 식별자
      data: DRIVER, // 경로 데이터 소스
      getPath: d => d.trip, // 각 경로의 경로를 가져오는 함수
      getTimestamps: d => d.timestamp, // 각 경로의 타임스탬프를 가져오는 함수
      getColor: d => d.board === 1 ? [255, 255, 255] : [255, 20, 147], // 탑승 상태에 따른 색상// 'board' 값이 1이면 탑승차 경로, 그렇지 않으면 빈차 경로
      opacity: 0.7, // 레이어의 불투명도
      widthMinPixels: 5, // 경로 선의 최소 너비
      trailLength: 12, // 이동 객체 뒤의 경로 길이
      currentTime: time, // 애니메이션을 위한 현재 시간
      shadowEnabled: false, // 그림자 비활성화
    }),

    // 운전자 마커를 시각화하는 레이어
    new ScatterplotLayer({
      id: 'driver-marker', // 레이어의 고유 식별자
      data: D_MARKER, // 운전자 마커 데이터 소스
      getPosition: d => d, // 각 마커의 위치를 가져오는 함수
      getFillColor: [255, 255, 255], // 마커의 채우기 색상
      getRadius: 3, // 마커의 반지름
      opacity: 0.5, // 마커의 불투명도
      pickable: false, // 선택(상호작용) 비활성화
      radiusScale: 4, // 반지름에 대한 스케일 팩터
      radiusMinPixels: 4, // 최소 반지름(픽셀)
      radiusMaxPixels: 8, // 최대 반지름(픽셀)
    }),
    
    // 승객 마커를 시각화하는 레이어
    new IconLayer({
      id: 'passenger-marker', // 레이어의 고유 식별자
      data: P_MARKER, // 승객 마커 데이터 소스
      pickable: false, // 선택(상호작용) 비활성화
      iconAtlas: ICON_PNG, // 아이콘 이미지 아틀라스
      iconMapping: ICON_MAPPING, // 아틀라스 내 아이콘 매핑
      sizeMinPixels: 20, // 아이콘의 최소 크기(픽셀)
      sizeMaxPixels: 15, // 아이콘의 최대 크기(픽셀)
      sizeScale: 5, // 크기에 대한 스케일 팩터
      getIcon: d => 'marker', // 아이콘 유형을 가져오는 함수
      getPosition: d => d, // 각 아이콘의 위치를 가져오는 함수
      getSize: d => 10, // 각 아이콘의 크기를 가져오는 함수
      getColor: d => [255, 255, 0] // 아이콘의 색상
    }),
  ];

  return (
    <div className='trip-container' style={{position: 'relative'}}>
      <DeckGL
        effects={DEFAULT_THEME.effects}
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
      >
        <Map
          mapStyle={mapStyle}
          mapboxAccessToken={MAPBOX_TOKEN}
        />
      </DeckGL>
      <h1 className='time'>
        TIME : {(String(parseInt(Math.round(time) / 60) % 24).length === 2) ? parseInt(Math.round(time) / 60) % 24 : '0'+String(parseInt(Math.round(time) / 60) % 24)} : {(String(Math.round(time) % 60).length === 2) ? Math.round(time) % 60 : '0'+String(Math.round(time) % 60)}
      </h1>
      <div className='subtext'>
        <div>- Total number of Vehicles in-service&nbsp; {CURRENT_RESULT.driving_vehicle_num+CURRENT_RESULT.empty_vehicle_num}</div>
        <div>- Number of Vehicles in Service&nbsp;: {CURRENT_RESULT.driving_vehicle_num || 0}</div>
        <div>- Number of Idle Vehicles&nbsp;: {CURRENT_RESULT.empty_vehicle_num || 0}</div>
        <div>- Number of Waiting Passengers&nbsp;: {CURRENT_RESULT.waiting_passenger_num || 0}</div>
        <div>- Current Average Waiting Time (minute)&nbsp;: {CURRENT_RESULT.average_waiting_time}</div>
        <div>- Cumulative Number of Request Failure&nbsp;: {CURRENT_RESULT.fail_passenger_cumNum}</div>
      </div>
    </div>
  );
}

export default Trip;