// Stats Loader for simulation_16
(function() {
    const statsData = {
        total_calls: 1575,
        failed_calls: 0,
        failure_rate: 0.0,
        vehicles_driven: 739
    };
    
    window.addEventListener('DOMContentLoaded', function() {
        console.log('통계 데이터 적용 중...', statsData);
        
        const totalCallsEl = document.getElementById('total-calls');
        const failedCallsEl = document.getElementById('total-failed-calls');
        const failureRateEl = document.getElementById('failure-rate');
        const vehiclesDrivenEl = document.getElementById('vehicles-driven');
        
        if (totalCallsEl) totalCallsEl.textContent = statsData.total_calls.toLocaleString();
        if (failedCallsEl) failedCallsEl.textContent = statsData.failed_calls.toLocaleString();
        if (failureRateEl) failureRateEl.textContent = statsData.failure_rate.toFixed(2);
        if (vehiclesDrivenEl) vehiclesDrivenEl.textContent = statsData.vehicles_driven.toLocaleString();
        
        console.log('통계 데이터 적용 완료!');
    });
})();
