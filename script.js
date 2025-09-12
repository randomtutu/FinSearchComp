// ============ Tabs logic ============
function activateTab(targetId) {
  const panels = document.querySelectorAll('.panel');
  const tabs = document.querySelectorAll('.tab');
  panels.forEach(p => p.hidden = true);
  tabs.forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
  });

  const targetPanel = document.getElementById(targetId);
  if (targetPanel) targetPanel.hidden = false;

  const tabButton = document.querySelector(`[aria-controls="${targetId}"]`);
  if (tabButton) {
    tabButton.classList.add('active');
    tabButton.setAttribute('aria-selected', 'true');
  }

  // 切到 leaderboard 时，刷新 Plotly 尺寸
  if (targetId === 'panel-leaderboard' && window.Plotly && window.__chartMounted) {
    const el = document.getElementById('global-chart');
    if (el) Plotly.Plots.resize(el);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  // 默认显示 Overview
  activateTab('panel-overview');

  // 绑定 Tab
  const tabOverview = document.getElementById('tab-overview');
  const tabLeaderboard = document.getElementById('tab-leaderboard');
  tabOverview.addEventListener('click', () => activateTab('panel-overview'));
  tabLeaderboard.addEventListener('click', () => activateTab('panel-leaderboard'));

  // 初始化图表
  renderGlobalChart();
});

// ============ Plotly chart (Global leaderboard) ============
function renderGlobalChart() {
  // 数据
  const models = [
    'Grok 4 (web)',
    'GPT-5 (web)',
    'Gemini 2.5 pro (web)',
    'GPT-5–thinking (web)',
    'DouBao non–thinking (web)',
    'Qwen3–235B–A22B–2507 (web)',
    'Yuanbao (DeepSeek V3) (web)',
    'Yuanbao (DeepSeek R1) (web)',
    'Yuanbao (T1 thinking) (web)',
    'DouBao thinking (web)',
    'Kimi K2 (web)',
    'DeepSeek R1 (web)',
    'Ernie X1 (web)'
  ];

  const scoresPct = [68.9, 46.8, 42.6, 41.1, 39.1, 37.4, 30.5, 29.8, 29.8, 29.8, 29.5, 17.2, 16.6];
  const scores = scoresPct.map(v => v / 100);

  // 颜色
  const barColor = 'rgba(145, 167, 255, 0.35)';
  const barLine  = 'rgba(145, 167, 255, 0.70)';

  // 构建图表
  const trace = {
    x: scores,
    y: models,
    type: 'bar',
    orientation: 'h',
    marker: {
      color: barColor,
      line: { color: barLine, width: 1 }
    },
    text: scoresPct.map(v => `${v.toFixed(1)}%`),
    textposition: 'outside',
    cliponaxis: false,
    hovertemplate: '<b>%{y}</b><br>Avg Score: %{x:.1%}<extra></extra>'
  };

  const layout = {
    title: {
      text: 'Model (Product) Avg Score on Global Subset',
      x: 0, xanchor: 'left',
      y: 0.98
    },
    margin: { l: 260, r: 30, t: 50, b: 50 },
    xaxis: {
      range: [0, 0.70],
      tickformat: '.1%',
      gridcolor: '#eef1f6',
      zeroline: false
    },
    yaxis: {
      automargin: true,
      autorange: 'reversed'
    },
    bargap: 0.18,
    paper_bgcolor: 'white',
    plot_bgcolor: 'white',
    showlegend: false
  };

  const config = { responsive: true, displayModeBar: false };
  const container = document.getElementById('global-chart');

  if (!container) return;
  Plotly.newPlot(container, [trace], layout, config).then(() => {
    window.__chartMounted = true;
  });

  window.addEventListener('resize', () => {
    if (window.__chartMounted) Plotly.Plots.resize(container);
  });
}
