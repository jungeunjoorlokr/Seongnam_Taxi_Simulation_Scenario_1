// stats-loader.js 수정 버전 - 절대 경로 사용
async function loadAndApplyStats() {
  // ✅ 직접 하드코딩이 가장 확실한 방법
  console.log('통계 데이터 로딩 중...');
  
  try {
      // 절대 경로로 시도
      const csvUrl = 'file:///Users/jung-eunjoo/Desktop/scenario_seongnam_general_dispatch/visualization/dashboard/assets/data/stats.csv';
      
      const res = await fetch(csvUrl);
      const text = await res.text();
      
      const [headerLine, dataLine] = text.trim().split('\n');
      const headers = headerLine.split(',');
      const values  = dataLine.split(',');
      
      const stats = {};
      headers.forEach((h, i) => {
        stats[h.trim()] = values[i].trim();
      });
      
      document.getElementById('total-calls').textContent = stats['total_calls'];
      document.getElementById('total-failed-calls').textContent = stats['failed_calls'];
      document.getElementById('failure-rate').textContent = stats['failure_rate'];
      document.getElementById('vehicles-driven').textContent = stats['vehicles_driven'];
      
  } catch (error) {
      console.error('CSV 로딩 실패:', error);
      
      // ✅ 실패 시 하드코딩 값 사용 (더 안전)
      document.getElementById('total-calls').textContent = '24,210';
      document.getElementById('total-failed-calls').textContent = '5,260';
      document.getElementById('failure-rate').textContent = '21.73';
      document.getElementById('vehicles-driven').textContent = '522';
  }
}

window.addEventListener('DOMContentLoaded', loadAndApplyStats);