import {useEffect, useState } from 'react';
import '../css/report.css'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, registerables } from "chart.js";
import { Pie, Bar } from 'react-chartjs-2';
// import legendImg from '../image/legend.png';
import legendImg from '../image/icon-atlas.png';
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, ...registerables);



const currResult = (data, time) => {
    const result = data.find(v => Number(v.time) === Math.floor(time));
    return result || {};
}


export default function Report(props){
    
    const [chartColors, setChartColors] = useState([
        'rgba(23, 184, 190, 0.8)',  // 기본: Dispatch
        'rgba(255, 153, 51, 0.8)',  // 기본: Operate
        'rgba(255, 255, 255, 1.0)'  // Idle
      ]);
      
        useEffect(() => {
            const fetchColors = async () => {
            try {
                const res = await fetch('http://localhost:8090/get-trip-colors');
                const data = await res.json();
                if (data.status === 'success') {
                const { boardingRGB, emptyRGB } = data;
        
                // Chart 색상
                setChartColors([
                    `rgba(${emptyRGB.join(',')}, 0.8)`,
                    `rgba(${boardingRGB.join(',')}, 0.8)`,
                    'rgba(255, 255, 255, 1.0)'
                ]);
        
                // DOM 색상
                document.querySelector('.dispatch-bar')?.style.setProperty('background-color', `rgb(${emptyRGB.join(',')})`);
                document.querySelector('.operating-bar')?.style.setProperty('background-color', `rgb(${boardingRGB.join(',')})`);
                }
            } catch (err) {
                console.error('색상 불러오기 실패:', err);
            }
            };
        
            fetchColors();
        }, []);
    
    const CURRENT_RESULT = currResult(props.data.RESULT, props.time);
    const CURRENT_WAITING_TIME = CURRENT_RESULT.current_waiting_time_dict || {};



    const data1 = {
        labels: ['Dispatched vehicles', 'Occupied vehicles', 'Idle vehicles'],
        datasets: [{
          label: 'count',
          data: [
            CURRENT_RESULT.dispatched_vehicle_num,
            CURRENT_RESULT.occupied_vehicle_num,
            CURRENT_RESULT.empty_vehicle_num
          ],
          backgroundColor: chartColors,
          borderColor: chartColors,
          borderWidth: 0,
        }]
      };
    const data2 = {
        labels: [5, 15, 25, 35, 45, 55],
        datasets: [
          {
            label: 'passenger (%)',
            data: Object.values(CURRENT_WAITING_TIME),
            borderColor: 'blue',
            Color: 'blue',
            fill: true,
            borderWidth: 0,
            barPercentage: 1,
            categoryPercentage: 1,
            hoverBackgroundColor: "darkgray",
            barThickness: "flex",
            backgroundColor: [
                'rgba(0, 0, 255, 0.5)'
            ]
          },
        ],
    };

    const options1= {
        maintainAspectRatio: false,
        responsive: true,
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: 'rgb(255, 255, 255)'
                }
            },
        }
    }    
    const options2= {
        maintainAspectRatio: false,
        responsive: true,
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: 'rgb(255, 255, 255)'
                }
            },
        },
        scales: {
            x: {
                type: 'linear',
                ticks: {
                    color: 'white',
                    stepSize: 10,
                    max: 60,
                    callback: function (value) {
                        return value.toString();
                    }
                },
                title: {
                    display: true,
                    align: 'center',
                    text: 'Waiting time(min)',
                    color: 'rgb(255, 255, 255)'
                }
            },
            y: {
                suggestedMin: 0,
                suggestedMax: 100,
                ticks: {
                    stepSize: 20,
                    color: 'white'
                }
            }
        }
    }
    return(
        <div className="report-container">
            <h1 className='report-header'>REPORT</h1>
            <div className='chart-container'>
                <div>
                    <Pie className="chart1" data={data1} options={options1}></Pie>
                </div>
                <div>
                    <Bar className="chart2" data={data2} options={options2}></Bar>
                </div>
            </div>
            <div className="legend-container">
            <div className="legend-box">
                <div className="legend-title">Legend</div>

                <div className="legend-item">
                <div className="legend-symbol marker"></div>
                <div>Requesting Passenger</div>
                </div>

                <div className="legend-item">
                <div className="legend-symbol"><div className="circle"></div></div>
                <div>Idling Vehicle</div>
                </div>

                <div className="legend-item">
                <div className="legend-symbol"><div className="bar dispatch-bar"></div></div>
                <div>Dispatching Vehicle</div>
                </div>

                <div className="legend-item">
                <div className="legend-symbol"><div className="bar operating-bar"></div></div>
                <div>Operating Vehicle</div>
                </div>
            </div>
            </div>
        </div>
    )
}