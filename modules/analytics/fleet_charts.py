import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

pio.renderers.default = "iframe"


# Generate vehicle and passenger status over time
def figure_4(base_path, time_range, time_single_labels, simulation_name=None, save_path=None):  
    # Determine folders to process
    if simulation_name:
        folders_to_process = [simulation_name]
    else:
        folders_to_process = [fd for fd in os.listdir(base_path) 
                            if not fd.startswith('.') and 
                            os.path.isdir(os.path.join(base_path, fd)) and 
                            fd.startswith("simulation_")]

    total_records = []
    for fd_nm in folders_to_process:
        records_path = os.path.join(base_path, fd_nm, 'record.csv')
        if os.path.exists(records_path):
            records = pd.read_csv(records_path)
            records = records[['time', 'waiting_passenger_cnt', 'empty_vehicle_cnt', 'driving_vehicle_cnt']]
            total_records.append(records)
    
    if not total_records:
        print("Figure 4: 데이터를 찾을 수 없습니다!")
        return
        
    total_records = pd.concat(total_records).reset_index(drop=True)
    total_records = total_records.groupby('time').mean().reset_index()
    
    # Create line chart
    fig_4 = go.Figure()
    fig_4.add_trace(go.Scatter(x=total_records['time'].tolist(), y=total_records['waiting_passenger_cnt'].tolist(),
                            mode="lines", 
                            name="Waiting passengers",
                            line=dict(width=3)))
    fig_4.add_trace(go.Scatter(x=total_records['time'].tolist(), y=total_records['empty_vehicle_cnt'].tolist(),
                            mode="lines",
                            name="Idle vehicles",
                            line=dict(width=3)))
    fig_4.add_trace(go.Scatter(x=total_records['time'].tolist(), y=total_records['driving_vehicle_cnt'].tolist(),
                            mode="lines",
                            name="In-service vehicles",
                            line=dict(width=3)))
    
    # Update layout
    fig_4.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=list(range(time_range[0], time_range[-1]+1, 60)),
            ticktext=time_single_labels + ['24:00'],
            range=[0, 1440],
            tickangle=45
        ),
        yaxis=dict(
            range=[0, 600],
            dtick=100
        )
    )
    
    fig_4.update_xaxes(title_text="Time")
    fig_4.update_yaxes(title_text="Number of vehicles and passengers")
    
    fig_4.update_layout(
        legend=dict(
            x=0.5,
            y=0.85,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1
        ),
        margin=dict(l=60, r=120, b=60, t=100, pad=10),
        template="plotly_white"
    )
    
    if save_path is not None:
        fig_4.write_html(f"{save_path}figure_4.html", config={'responsive': True})
    else: 
        return fig_4


# Generate hourly operating vehicle count bar chart
def figure_5(base_path, time_bins, time_single_labels, simulation_name=None, save_path=None):  
    # Determine folders to process
    if simulation_name:
        folders_to_process = [simulation_name]
    else:
        folders_to_process = [fd for fd in os.listdir(base_path) 
                            if not fd.startswith('.') and 
                            os.path.isdir(os.path.join(base_path, fd)) and 
                            fd.startswith("simulation_")]

    total_operating_vh_cnt = []
    
    # Fix time_bins to remove infinite value
    time_bins_fixed = time_bins[:-1] + [time_bins[-2] + 60]
    
    for fd_nm in folders_to_process:
        records_path = os.path.join(base_path, fd_nm, 'record.csv')
        if os.path.exists(records_path):
            records = pd.read_csv(records_path)
            records['operating_vehicle_cnt'] = records['empty_vehicle_cnt'] + records['driving_vehicle_cnt']
            
            records['time_cat'] = pd.cut(records['time'], bins=time_bins_fixed, labels=time_single_labels, right=False)
            records = records[['time_cat', 'operating_vehicle_cnt']]
            
            operating_vh_cnt = records.groupby('time_cat').max('operating_vehicle_cnt').reset_index()
            total_operating_vh_cnt.append(operating_vh_cnt)
    
    if not total_operating_vh_cnt:
        print("Figure 5: 데이터를 찾을 수 없습니다!")
        return
        
    total_operating_vh_cnt = pd.concat(total_operating_vh_cnt).reset_index(drop=True)
    total_operating_vh_cnt = total_operating_vh_cnt.groupby('time_cat').mean().reset_index()
    total_operating_vh_cnt['operating_vehicle_cnt'] = round(total_operating_vh_cnt['operating_vehicle_cnt']).astype(int)
    
    # Create bar chart
    fig_5 = px.bar(x=total_operating_vh_cnt['time_cat'], y=total_operating_vh_cnt['operating_vehicle_cnt'])
    
    fig_5.update_layout(
        xaxis=dict(
            tickmode='array',
            title="Time",
            tickangle=45
        ),
        yaxis=dict(
            title="number of vehicles"
        ),
        margin=dict(l=60, r=60, b=60, t=40, pad=10),
        template="plotly_white"
    )
    
    fig_5.update_traces(
        textposition='outside',
        texttemplate=[f'<b>{cnt}</b>' for cnt in total_operating_vh_cnt['operating_vehicle_cnt']],
        textfont=dict(size=16, family='Arial Black')
    )
    
    if save_path is not None:
        fig_5.write_html(f"{save_path}figure_5.html", config={'responsive': True})
    else:
        return fig_5