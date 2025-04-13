// Global variables
let performanceChart = null;
let selectedDevices = [];
let currentMetric = 'cpu_usage';
let timeRange = 7; // Default: 7 days
let deviceColors = {};
let chartData = {};

// Color palette for devices
const colorPalette = [
  '#1976d2', '#2196f3', '#64b5f6', '#bbdefb',  // Blues
  '#388e3c', '#4caf50', '#81c784', '#c8e6c9',  // Greens
  '#d32f2f', '#f44336', '#e57373', '#ffcdd2',  // Reds
  '#ffa000', '#ffc107', '#ffd54f', '#ffecb3',  // Ambers
  '#7b1fa2', '#9c27b0', '#ba68c8', '#e1bee7',  // Purples
  '#00796b', '#009688', '#4db6ac', '#b2dfdb',  // Teals
];

// Initialize the page
$(document).ready(function() {
  // Initialize device selection dropdown
  $('#deviceSelection').change(updateSelectedDevices);
  
  // Initialize metric selection
  $('#metricSelection').change(function() {
    currentMetric = $(this).val();
    updateChartTitle();
    loadPerformanceData();
  });
  
  // Handle time range selection
  $('.time-btn').click(function() {
    $('.time-btn').removeClass('active');
    $(this).addClass('active');
    
    // Get selected time range in days (0 means custom)
    timeRange = parseInt($(this).data('days'));
    
    if (timeRange > 0) {
      loadPerformanceData();
    }
  });
  
  // Custom date range
  $('#applyCustomRange').click(function() {
    const startDate = $('#startDate').val();
    const endDate = $('#endDate').val();
    
    if (startDate && endDate) {
      // Hide modal
      $('#customRangeModal').modal('hide');
      
      // Set custom range text on button
      const customRangeBtn = $('.time-btn[data-days="0"]');
      customRangeBtn.text('Custom Range');
      
      // Activate custom button
      $('.time-btn').removeClass('active');
      customRangeBtn.addClass('active');
      
      // Load data with custom range
      loadPerformanceData(startDate, endDate);
    } else {
      alert('Please select both start and end dates');
    }
  });
  
  // Initialize refresh button
  $('#refreshButton').click(function() {
    loadPerformanceData();
  });
  
  // Initialize chart
  const ctx = document.getElementById('performanceChart').getContext('2d');
  performanceChart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: []
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      scales: {
        x: {
          type: 'time',
          time: {
            unit: 'day'
          },
          title: {
            display: true,
            text: 'Date/Time'
          }
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'CPU Usage (%)'
          }
        }
      },
      plugins: {
        tooltip: {
          callbacks: {
            title: function(context) {
              return new Date(context[0].parsed.x).toLocaleString();
            }
          }
        },
        legend: {
          display: false
        }
      }
    }
  });
  
  // Set today's date as max for date inputs
  const today = new Date().toISOString().split('T')[0];
  $('#endDate').attr('max', today);
  
  // Initial load with default settings
  updateChartTitle();
  loadPerformanceData();
});

// Update selected devices when the selection changes
function updateSelectedDevices() {
  // Get selected device IDs
  selectedDevices = $('#deviceSelection').val() || [];
  
  // Create tags for selected devices
  updateSelectedDevicesTags();
  
  // Update chart if devices changed
  if (selectedDevices.length > 0) {
    loadPerformanceData();
  } else {
    clearChart();
  }
}

// Update visual tags for selected devices
function updateSelectedDevicesTags() {
  const tagsContainer = $('#selectedDevicesTags');
  tagsContainer.empty();
  
  // Create a tag for each selected device
  $('#deviceSelection option:selected').each(function() {
    const deviceId = $(this).val();
    const deviceName = $(this).text();
    
    // Assign a color to the device if not already assigned
    if (!deviceColors[deviceId]) {
      deviceColors[deviceId] = colorPalette[Object.keys(deviceColors).length % colorPalette.length];
    }
    
    // Create and append tag
    const tag = $('<span class="device-badge"></span>')
      .text(deviceName)
      .css('background-color', hexToRgba(deviceColors[deviceId], 0.2))
      .css('border-color', hexToRgba(deviceColors[deviceId], 0.5));
    
    // Add remove icon
    const removeIcon = $('<i class="fas fa-times"></i>').click(function(e) {
      e.stopPropagation();
      
      // Remove from selectedDevices array
      const index = selectedDevices.indexOf(deviceId);
      if (index > -1) {
        selectedDevices.splice(index, 1);
      }
      
      // Update select element
      const option = $('#deviceSelection option[value="' + deviceId + '"]');
      option.prop('selected', false);
      
      // Remove tag and update chart
      tag.remove();
      loadPerformanceData();
    });
    
    tag.append(removeIcon);
    tagsContainer.append(tag);
  });
}

// Update chart title based on selected metric
function updateChartTitle() {
  const metricLabels = {
    'cpu_usage': 'CPU Usage (%)',
    'temperature': 'Temperature (°C)',
    'latency': 'Latency (ms)',
    'bandwidth': 'Bandwidth (Mbps)'
  };
  
  $('#chartTitle').text(`${metricLabels[currentMetric]} Over Time`);
  $('#tableMetricHeader').text(metricLabels[currentMetric]);
}

// Load performance data from the server
function loadPerformanceData(startDate = null, endDate = null) {
  if (selectedDevices.length === 0) {
    clearChart();
    return;
  }
  
  // Show loading modal
  $('#loadingModal').modal('show');
  
  // Prepare request data
  const requestData = {
    device_ids: selectedDevices,
    metric: currentMetric,
    days: timeRange
  };
  
  // Add custom date range if provided
  if (startDate && endDate) {
    requestData.start_date = startDate;
    requestData.end_date = endDate;
  }
  
  // CSRF token for POST request
  const csrfToken = $('input[name="csrfmiddlewaretoken"]').val();
  
  // Fetch data from API
  $.ajax({
    url: '/api/performance-data/',
    type: 'POST',
    data: JSON.stringify(requestData),
    contentType: 'application/json',
    headers: {
      'X-CSRFToken': csrfToken
    },
    success: function(response) {
      // Hide loading modal
      $('#loadingModal').modal('hide');
      
      // Store the data for later use (e.g., export)
      chartData = response;
      
      // Update chart with new data
      updateChart(response);
      
      // Update summary stats
      updateSummaryStats(response);
      
      // Update data table
      updateDataTable(response);
      
      // Update chart legend
      updateChartLegend();
    },
    error: function(error) {
      // Hide loading modal
      $('#loadingModal').modal('hide');
      
      console.error('Error fetching performance data:', error);
      alert('Failed to load performance data. Please try again.');
    }
  });
}

// Update chart with new data
function updateChart(data) {
  // Clear existing datasets
  performanceChart.data.datasets = [];
  
  // Update y-axis label
  const metricLabels = {
    'cpu_usage': 'CPU Usage (%)',
    'temperature': 'Temperature (°C)',
    'latency': 'Latency (ms)',
    'bandwidth': 'Bandwidth (Mbps)'
  };
  
  performanceChart.options.scales.y.title.text = metricLabels[currentMetric];
  
  // Define thresholds for annotations based on metric
  let threshold = 0;
  switch(currentMetric) {
    case 'cpu_usage':
      threshold = 80; // 80% CPU is high
      break;
    case 'temperature':
      threshold = 70; // 70°C is high for most devices
      break;
    case 'latency':
      threshold = 100; // 100ms is high latency
      break;
    case 'bandwidth':
      threshold = 10; // 10Mbps is low bandwidth (context dependent)
      break;
  }
  
  // Add annotation for threshold
  performanceChart.options.plugins.annotation = {
    annotations: {
      thresholdLine: {
        type: 'line',
        yMin: threshold,
        yMax: threshold,
        borderColor: currentMetric === 'bandwidth' ? 'rgba(255, 159, 64, 0.7)' : 'rgba(255, 99, 132, 0.7)',
        borderWidth: 2,
        borderDash: [6, 6],
        label: {
          enabled: true,
          content: currentMetric === 'bandwidth' ? 'Minimum Recommended' : 'Warning Threshold',
          position: 'end'
        }
      }
    }
  };
  
  // Add datasets for each device
  for (const deviceId in data.devices) {
    const deviceInfo = data.devices[deviceId];
    const deviceDataset = {
      label: deviceInfo.name,
      data: deviceInfo.data.map(point => ({
        x: new Date(point.timestamp),
        y: point.value
      })),
      borderColor: deviceColors[deviceId] || getRandomColor(),
      backgroundColor: hexToRgba(deviceColors[deviceId] || getRandomColor(), 0.1),
      borderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
      tension: 0.1
    };
    
    performanceChart.data.datasets.push(deviceDataset);
  }
  
  // Adjust time unit based on selected time range
  if (timeRange <= 1) {
    performanceChart.options.scales.x.time.unit = 'hour';
  } else if (timeRange <= 7) {
    performanceChart.options.scales.x.time.unit = 'day';
  } else {
    performanceChart.options.scales.x.time.unit = 'week';
  }
  
  // Update chart
  performanceChart.update();
}

// Update summary statistics
function updateSummaryStats(data) {
  const statsContainer = $('#summaryStats');
  statsContainer.empty();
  
  // Create stats cards for each device
  for (const deviceId in data.devices) {
    const deviceInfo = data.devices[deviceId];
    const values = deviceInfo.data.map(point => point.value);
    
    // Calculate statistics
    const avg = values.length > 0 ? (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2) : 'N/A';
    const min = values.length > 0 ? Math.min(...values).toFixed(2) : 'N/A';
    const max = values.length > 0 ? Math.max(...values).toFixed(2) : 'N/A';
    const current = values.length > 0 ? values[values.length - 1].toFixed(2) : 'N/A';
    
    // Create stat card
    const card = $(`
      <div class="col-md-6 col-lg-3">
        <div class="card">
          <div class="card-header" style="background-color: ${hexToRgba(deviceColors[deviceId], 0.1)}; border-left: 4px solid ${deviceColors[deviceId]}">
            ${deviceInfo.name}
          </div>
          <div class="card-body">
            <div class="row">
              <div class="col-6">
                <div class="metric-card">
                  <div class="metric-label">Average</div>
                  <div class="metric-value">${avg}</div>
                </div>
              </div>
              <div class="col-6">
                <div class="metric-card">
                  <div class="metric-label">Current</div>
                  <div class="metric-value">${current}</div>
                </div>
              </div>
              <div class="col-6">
                <div class="metric-card">
                  <div class="metric-label">Minimum</div>
                  <div class="metric-value">${min}</div>
                </div>
              </div>
              <div class="col-6">
                <div class="metric-card">
                  <div class="metric-label">Maximum</div>
                  <div class="metric-value">${max}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `);
    
    statsContainer.append(card);
  }
}

// Update data table
function updateDataTable(data) {
  const tableBody = $('#tableBody');
  tableBody.empty();
  
  // Collect all data points for sorting
  let allPoints = [];
  
  for (const deviceId in data.devices) {
    const deviceInfo = data.devices[deviceId];
    
    // Add device info to each data point
    const devicePoints = deviceInfo.data.map(point => ({
      deviceId: deviceId,
      deviceName: deviceInfo.name,
      timestamp: point.timestamp,
      value: point.value,
      status: point.status
    }));
    
    allPoints = allPoints.concat(devicePoints);
  }
  
  // Sort by timestamp, most recent first
  allPoints.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  
  // Limit to 100 rows for performance
  allPoints = allPoints.slice(0, 100);
  
  // Add rows to table
  for (const point of allPoints) {
    const row = $('<tr></tr>');
    
    // Format timestamp
    const timestamp = new Date(point.timestamp).toLocaleString();
    
    // Determine status icon and color
    const statusIcon = point.status === 'Up' ? 
      '<i class="fas fa-check-circle status-up"></i>' : 
      '<i class="fas fa-exclamation-circle status-down"></i>';
    
    // Add cells
    row.append(`<td>${timestamp}</td>`);
    row.append(`<td style="border-left: 3px solid ${deviceColors[point.deviceId]}">${point.deviceName}</td>`);
    row.append(`<td>${point.value.toFixed(2)}</td>`);
    row.append(`<td>${statusIcon} ${point.status}</td>`);
    
    tableBody.append(row);
  }
}

// Update chart legend
function updateChartLegend() {
  const legendContainer = $('#chartLegend');
  legendContainer.empty();
  
  // Create legend list
  const legendList = $('<ul></ul>');
  
  // Add legend item for each dataset
  performanceChart.data.datasets.forEach(dataset => {
    const legendItem = $('<li></li>');
    
    // Create color box
    const colorBox = $('<span class="legend-color"></span>')
      .css('background-color', dataset.borderColor);
    
    // Create label
    const label = $('<span></span>').text(dataset.label);
    
    legendItem.append(colorBox, label);
    legendList.append(legendItem);
  });
  
  legendContainer.append(legendList);
}

// Clear chart and related displays
function clearChart() {
  // Clear chart datasets
  if (performanceChart) {
    performanceChart.data.datasets = [];
    performanceChart.update();
  }
  
  // Clear summary stats and table
  $('#summaryStats').empty();
  $('#tableBody').empty();
  $('#chartLegend').empty();
}

// Export chart as image (PNG or JPG)
function exportToImage(format) {
  const canvas = document.getElementById('performanceChart');
  
  if (format === 'jpg') {
    // For JPEG, set white background
    const context = canvas.getContext('2d');
    const currentFill = context.fillStyle;
    context.fillStyle = 'white';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = currentFill;
  }
  
  const imageURL = canvas.toDataURL(`image/${format}`, 1.0);
  
  // Create and trigger download
  const link = document.createElement('a');
  link.download = `performance_${currentMetric}_${new Date().toISOString().slice(0,10)}.${format}`;
  link.href = imageURL;
  link.click();
}

// Export chart as PDF
function exportToPDF() {
  // Use html2canvas to capture the chart
  html2canvas(document.getElementById('performanceChart')).then(canvas => {
    const imageData = canvas.toDataURL('image/png');
    
    // Create PDF document
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF('l', 'mm', 'a4'); // Landscape mode
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    
    // Add title
    pdf.setFontSize(16);
    pdf.text(`Performance Monitoring: ${$('#chartTitle').text()}`, 10, 10);
    
    // Add timestamp
    pdf.setFontSize(10);
    pdf.text(`Generated: ${new Date().toLocaleString()}`, 10, 18);
    
    // Add chart image
    const imgWidth = pageWidth - 20;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    pdf.addImage(imageData, 'PNG', 10, 25, imgWidth, imgHeight);
    
    // Save PDF
    pdf.save(`performance_report_${currentMetric}_${new Date().toISOString().slice(0,10)}.pdf`);
  });
}

// Export data to CSV
function exportToCSV() {
  if (!chartData || Object.keys(chartData.devices).length === 0) {
    alert('No data to export');
    return;
  }
  
  // Create CSV header
  let csvContent = 'Timestamp,Device,';
  
  // Add metric name
  const metricLabels = {
    'cpu_usage': 'CPU Usage (%)',
    'temperature': 'Temperature (°C)',
    'latency': 'Latency (ms)',
    'bandwidth': 'Bandwidth (Mbps)'
  };
  csvContent += `${metricLabels[currentMetric]},Status\n`;
  
  // Collect all data points
  let allPoints = [];
  
  for (const deviceId in chartData.devices) {
    const deviceInfo = chartData.devices[deviceId];
    
    // Add device info to each data point
    const devicePoints = deviceInfo.data.map(point => ({
      deviceName: deviceInfo.name,
      timestamp: point.timestamp,
      value: point.value,
      status: point.status
    }));
    
    allPoints = allPoints.concat(devicePoints);
  }
  
  // Sort by timestamp
  allPoints.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  
  // Add rows to CSV
  for (const point of allPoints) {
    const row = [
      `"${new Date(point.timestamp).toLocaleString()}"`,
      `"${point.deviceName}"`,
      point.value.toFixed(2),
      `"${point.status}"`
    ].join(',');
    
    csvContent += row + '\n';
  }
  
  // Create and trigger download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `performance_data_${currentMetric}_${new Date().toISOString().slice(0,10)}.csv`;
  link.click();
}

// Export data table
function exportDataTable() {
  const table = document.getElementById('dataTable');
  const rows = table.querySelectorAll('tr');
  
  // Create CSV content
  let csvContent = '';
  
  // Add header row
  const headerCells = rows[0].querySelectorAll('th');
  const headerRow = Array.from(headerCells).map(cell => `"${cell.textContent}"`).join(',');
  csvContent += headerRow + '\n';
  
  // Add data rows
  for (let i = 1; i < rows.length; i++) {
    const cells = rows[i].querySelectorAll('td');
    const rowData = Array.from(cells).map(cell => {
      // Remove any HTML, just get text content
      return `"${cell.textContent.trim()}"`;
    }).join(',');
    
    csvContent += rowData + '\n';
  }
  
  // Create and trigger download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `device_performance_table_${new Date().toISOString().slice(0,10)}.csv`;
  link.click();
}

// Helper function to get random color
function getRandomColor() {
  return colorPalette[Math.floor(Math.random() * colorPalette.length)];
}

// Helper function to convert hex color to rgba
function hexToRgba(hex, alpha) {
  // Default to a blue color if hex is undefined
  if (!hex) {
    return `rgba(25, 118, 210, ${alpha})`;
  }
  
  // Remove # if present
  hex = hex.replace('#', '');
  
  // Parse hex values
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  
  // Return rgba
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}