// Smooth scrolling for navigation links
function initSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Initialize card modal functionality
function initCardModals() {
    const modal = document.getElementById('contentModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalContent = document.getElementById('modalContent');
    const closeModals = document.querySelectorAll('.close-modal');
    const readMoreBtns = document.querySelectorAll('.read-more-btn');
    const cardContents = document.querySelectorAll('.card-content');
    
    // Close modals when clicking the close button
    closeModals.forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            document.querySelectorAll('.modal').forEach(modal => {
                modal.style.display = 'none';
            });
            document.body.style.overflow = 'auto';
        });
    });
    
    // Close modals when clicking outside the modal content
    window.addEventListener('click', (event) => {
        if (event.target.classList.contains('modal')) {
            document.querySelectorAll('.modal').forEach(modal => {
                modal.style.display = 'none';
            });
            document.body.style.overflow = 'auto';
        }
    });
    
    // Open modal when clicking read more button
    readMoreBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const card = btn.closest('.card-content');
            const title = card.querySelector('.title').textContent;
            const fullContent = card.querySelector('.card-full-content').innerHTML;
            
            modalTitle.textContent = title;
            modalContent.innerHTML = fullContent;
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        });
    });
    
    // Note: Removed card click functionality to avoid duplicate modal triggers
    // Only read more button will trigger the modal now
}

// Add fade-in animation to sections on scroll
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.section, .box').forEach(el => {
        observer.observe(el);
    });
}

// Removed initExpandButtons function - using modal popup instead

// Initialize findings carousel
function initFindingsCarousel() {
    const carousel = document.querySelector('.findings-carousel');
    if (!carousel) return;
    
    const carouselInner = carousel.querySelector('.findings-carousel-inner');
    const items = carousel.querySelectorAll('.carousel-item');
    const prevBtn = carousel.querySelector('.carousel-prev');
    const nextBtn = carousel.querySelector('.carousel-next');
    const indicators = carousel.querySelectorAll('.indicator');
    
    let currentIndex = 0;
    const totalItems = items.length;
    
    // Set initial active state
    updateCarousel();
    
    // Event listeners for navigation buttons
    prevBtn.addEventListener('click', () => {
        currentIndex = (currentIndex - 1 + totalItems) % totalItems;
        updateCarousel();
    });
    
    nextBtn.addEventListener('click', () => {
        currentIndex = (currentIndex + 1) % totalItems;
        updateCarousel();
    });
    
    // Event listeners for indicators
    indicators.forEach((indicator, index) => {
        indicator.addEventListener('click', () => {
            currentIndex = index;
            updateCarousel();
        });
    });
    
    // Update carousel position and active states
    function updateCarousel() {
        // Update carousel position
        carouselInner.style.transform = `translateX(-${currentIndex * 90}%)`;
        
        // Update active indicator
        indicators.forEach((indicator, index) => {
            if (index === currentIndex) {
                indicator.classList.add('active');
            } else {
                indicator.classList.remove('active');
            }
        });
    }
}

// Lazy load chart when container becomes visible
function initChartLazyLoading() {
    const chartContainer = document.getElementById('global-chart');
    if (!chartContainer) return;
    
    const chartObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !window.__chartMounted) {
                loadPlotly().then(() => {
                    renderGlobalChart();
                    // Hide loading indicator
                    const loadingEl = document.getElementById('chart-loading');
                    if (loadingEl) {
                        loadingEl.style.display = 'none';
                    }
                });
                chartObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });
    
    chartObserver.observe(chartContainer);
}

// Lazy load images when they become visible
function initImageLazyLoading() {
    const lazyImages = document.querySelectorAll('.lazy-image');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.classList.add('loading');
                    
                    const tempImg = new Image();
                    tempImg.onload = () => {
                        img.src = img.dataset.src;
                        img.classList.remove('loading');
                        img.classList.add('loaded');
                        img.removeAttribute('data-src');
                    };
                    tempImg.src = img.dataset.src;
                    
                    imageObserver.unobserve(img);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '50px 0px'
        });
        
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    } else {
        // Fallback for browsers without IntersectionObserver
        lazyImages.forEach(img => {
            img.src = img.dataset.src;
            img.classList.add('loaded');
            img.removeAttribute('data-src');
        });
    }
}

// Initialize image zoom functionality
function initImageZoom() {
    const imageModal = document.getElementById('imageModal');
    const zoomedImage = document.getElementById('zoomedImage');
    const zoomableImages = document.querySelectorAll('.zoomable-image');
    
    zoomableImages.forEach(img => {
        img.addEventListener('click', () => {
            zoomedImage.src = img.src || img.dataset.src;
            imageModal.style.display = 'block';
            document.body.style.overflow = 'hidden';
        });
    });
    
    // Close image modal when clicking outside
    imageModal.addEventListener('click', (e) => {
        if (e.target === imageModal) {
            imageModal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
}

// Page initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functionality
    initSmoothScrolling();
    initCardModals();
    initScrollAnimations();
    initChartLazyLoading();
    initImageLazyLoading();
    initImageZoom();
    initFindingsCarousel();
});
    
    // Add resize listener for chart responsiveness
    window.addEventListener('resize', function() {
        if (window.Plotly && document.getElementById('global-chart') && window.__chartMounted) {
            Plotly.Plots.resize('global-chart');
        }
    });

// ============ Plotly chart (Global leaderboard) ============
function renderGlobalChart() {
  // 数据
  const models = [
    'Grok 4 (web)',
    'GPT-5-Thinking (web)',
    'Gemini 2.5 pro (web)',
    'DouBao (web)',
    'Qwen3-235B-A22B-2507 (web)',
    'YuanBao (DeepSeek V3) (web)',
    'YuanBao (HunYuan-T1-Thinking) (web)',
    'YuanBao (DeepSeek R1) (web)',
    'DouBao-Thinking (web)',
    'Kimi k2 (web)',
    'DeepSeek R1 (web)',
    'ERNIE X1 (web)'
  ];

  const scoresPct = [68.9, 63.9, 42.6, 39.1, 37.4, 30.5, 29.8, 29.8, 29.8, 29.5, 17.2, 16.6];
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
