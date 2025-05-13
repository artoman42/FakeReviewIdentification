document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('reviewForm');
    const resultDiv = document.getElementById('result');
  
    form.addEventListener('submit', function (event) {
      event.preventDefault();
  
      const reviewLink = document.getElementById('reviewLink').value;
      const showFakeDetails = document.getElementById('toggleFake').checked;
  
      fetch('/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reviewLink: reviewLink }),
      })
      .then(response => response.json())
      .then(data => {
        resultDiv.innerHTML = '';
  
        // Display summary information
        const productName = document.createElement('p');
        productName.innerHTML = `<strong>${data.product_name}</strong>`;
        resultDiv.appendChild(productName);
  
        const overallSentiment = document.createElement('p');
        overallSentiment.innerHTML = `<strong>Загальна оцінка емоційного забарвлення:</strong> ${data.overall_sentiment}`;
        resultDiv.appendChild(overallSentiment);
  
        const cleanOverall = document.createElement('p');
        cleanOverall.innerHTML = `<strong>Оцінка без фейкових та AI-згенерованих відгуків:</strong> ${data.clean_overall_sentiment}`;
        resultDiv.appendChild(cleanOverall);
  
        const recommendation = document.createElement('p');
        recommendation.innerHTML = `<strong>Висновок:</strong> ${data.recommendation}`;
        resultDiv.appendChild(recommendation);
  
        // Create a flex container for the two bar charts
        const chartsWrapper = document.createElement('div');
        chartsWrapper.classList.add('charts-wrapper');
  
        // Container for overall sentiment distribution (all reviews)
        const overallChartContainer = document.createElement('div');
        overallChartContainer.classList.add('chart-container');
        overallChartContainer.innerHTML = '<canvas id="sentimentChart"></canvas>';
        chartsWrapper.appendChild(overallChartContainer);
  
        // Container for clean sentiment distribution (filtered reviews)
        const cleanChartContainer = document.createElement('div');
        cleanChartContainer.classList.add('chart-container');
        cleanChartContainer.innerHTML = '<canvas id="cleanChart"></canvas>';
        chartsWrapper.appendChild(cleanChartContainer);
  
        resultDiv.appendChild(chartsWrapper);
  
        // Create container for the pie chart (fake/AI/normal reviews)
        const pieChartContainer = document.createElement('div');
        pieChartContainer.classList.add('pie-chart-container');
        pieChartContainer.innerHTML = '<canvas id="pieChart"></canvas>';
        resultDiv.appendChild(pieChartContainer);
  
        // Render reviews
        data.results.forEach(review => {
          const reviewElement = document.createElement('div');
          reviewElement.classList.add('review');
  
          if (review.hasOwnProperty('fake_class')) {
            if (review.fake_class === 0) {
              reviewElement.classList.add('review-normal');
            } else if (review.fake_class === 1) {
              reviewElement.classList.add('review-fake');
            } else if (review.fake_class === 2) {
              reviewElement.classList.add('review-ai');
            }
          }
  
          reviewElement.innerHTML = `
            <p><strong>Нікнейм:</strong> ${review.nickname}</p>
            <p><strong>Відгук:</strong> ${review.text}</p>
            <p><strong>Оцінка:</strong> ${review.sentiment}</p>
          `;
  
          if (showFakeDetails && review.hasOwnProperty('fake_class')) {
            let fakeTypeText = '';
            switch (review.fake_class) {
              case 0:
                fakeTypeText = 'Нормальний';
                break;
              case 1:
                fakeTypeText = 'Фейковий';
                break;
              case 2:
                fakeTypeText = 'AI-згенерований';
                break;
              default:
                fakeTypeText = 'Невідомо';
            }
            const fakeInfo = document.createElement('p');
            fakeInfo.innerHTML = `<strong>Fake Аналіз:</strong> Тип: ${fakeTypeText} | Імовірність: ${(review.fake_score * 100).toFixed(2)}%`;
            reviewElement.appendChild(fakeInfo);
          }
          resultDiv.appendChild(reviewElement);
        });
  
        // Render overall sentiment distribution chart for all reviews
        const sentimentCtx = document.getElementById('sentimentChart').getContext('2d');
        new Chart(sentimentCtx, {
          type: 'bar',
          data: {
            labels: ['1', '2', '3', '4', '5'],
            datasets: [{
              label: 'Кількість відгуків',
              data: [
                data.distribution[1],
                data.distribution[2],
                data.distribution[3],
                data.distribution[4],
                data.distribution[5]
              ],
              backgroundColor: 'rgba(75, 192, 192, 0.5)',
              borderColor: 'rgba(75, 192, 192, 1)',
              borderWidth: 1
            }]
          },
          options: {
            scales: { y: { beginAtZero: true } },
            plugins: { title: { display: true, text: 'Розподіл оцінок (усі відгуки)' } }
          }
        });
  
        // Render clean sentiment distribution chart for normal reviews only
        const cleanCtx = document.getElementById('cleanChart').getContext('2d');
        new Chart(cleanCtx, {
          type: 'bar',
          data: {
            labels: ['1', '2', '3', '4', '5'],
            datasets: [{
              label: 'Кількість відгуків (без фейкових/AI)',
              data: [
                data.clean_distribution[1],
                data.clean_distribution[2],
                data.clean_distribution[3],
                data.clean_distribution[4],
                data.clean_distribution[5]
              ],
              backgroundColor: 'rgba(153, 102, 255, 0.5)',
              borderColor: 'rgba(153, 102, 255, 1)',
              borderWidth: 1
            }]
          },
          options: {
            scales: { y: { beginAtZero: true } },
            plugins: { title: { display: true, text: 'Розподіл оцінок (без фейкових/AI)' } }
          }
        });
  
        // Calculate fake/AI/normal distribution for the pie chart
        const fakeDistribution = { 'Нормальний': 0, 'Фейковий': 0, 'AI-згенерований': 0 };
        data.results.forEach(review => {
          if (review.hasOwnProperty('fake_class')) {
            if (review.fake_class === 0) {
              fakeDistribution['Нормальний']++;
            } else if (review.fake_class === 1) {
              fakeDistribution['Фейковий']++;
            } else if (review.fake_class === 2) {
              fakeDistribution['AI-згенерований']++;
            }
          }
        });
  
        // Render pie chart for fake/AI/normal review distribution
        const pieCtx = document.getElementById('pieChart').getContext('2d');
        new Chart(pieCtx, {
          type: 'pie',
          data: {
            labels: Object.keys(fakeDistribution),
            datasets: [{
              label: 'Fake Аналіз',
              data: Object.values(fakeDistribution),
              backgroundColor: [
                'rgba(75, 192, 192, 0.5)', // Normal: greenish/teal
                'rgba(255, 99, 132, 0.5)',  // Fake: red
                'rgba(54, 162, 235, 0.5)'   // AI-generated: blue
              ],
              borderColor: [
                'rgba(75, 192, 192, 1)',
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)'
              ],
              borderWidth: 1
            }]
          },
          options: {
            plugins: {
              legend: { position: 'top' },
              title: { display: true, text: 'Розподіл фейкового аналізу' }
            }
          }
        });
      })
      .catch(error => console.error('Error:', error));
    });
  
    const toggleFakeCheckbox = document.getElementById('toggleFake');
    toggleFakeCheckbox.addEventListener('change', () => {
      // Optionally trigger a re-render based on the toggle state
    });
  });
  