// 智能看板JavaScript主文件
class SmartDashboardManager {
    constructor() {
        this.currentData = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkConnection();
    }

    bindEvents() {
        document.getElementById('queryInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.executeQuery();
        });
    }

    async checkConnection() {
        try {
            const response = await this.callPythonScript('test_connection');
            this.updateConnectionStatus(response.success);
        } catch (error) {
            this.updateConnectionStatus(false);
        }
    }

    updateConnectionStatus(connected) {
        const status = document.getElementById('connectionStatus');
        status.textContent = connected ? '🟢 已连接' : '🔴 未连接';
        status.style.color = connected ? '#28a745' : '#dc3545';
    }

    async executeQuery() {
        const query = document.getElementById('queryInput').value.trim();
        if (!query) {
            this.showError('请输入查询描述');
            return;
        }

        this.showLoading();
        
        try {
            const result = await this.callPythonScript('execute_query', {query});
            
            if (result.success) {
                this.currentData = result;
                this.renderDashboard(result);
            } else {
                this.showError(result.error || '查询失败');
            }
        } catch (error) {
            this.showError('查询执行出错: ' + error.message);
        }
    }

    async callPythonScript(action, params = {}) {
        // 这个方法会被Python脚本重写
        console.log(`调用: ${action}`, params);
        
        if (action === 'test_connection') {
            return {success: true};
        }
        
        throw new Error('未实现的操作');
    }

    renderDashboard(result) {
        const container = document.getElementById('dashboardContainer');
        let html = '';

        // 主结果展示
        html += this.generateMainCard(result);
        
        // 调试信息
        if (result.query_plan) {
            html += this.generateDebugInfo(result);
        }

        container.innerHTML = html;

        // 初始化图表
        if (result.chart_type === 'line_chart' || result.chart_type === 'bar_chart') {
            this.initChart(result);
        }
    }

    generateMainCard(result) {
        if (!result.data || result.data.length === 0) {
            return `
                <div class="card">
                    <div class="card-title">查询结果</div>
                    <div class="loading">
                        <div>📭 查询成功，但没有找到数据</div>
                    </div>
                </div>
            `;
        }

        switch (result.chart_type) {
            case 'single_value':
                return this.createSingleValueCard(result);
            case 'table':
                return this.createTableCard(result);
            case 'line_chart':
                return this.createChartCard(result, 'line');
            case 'bar_chart':
                return this.createChartCard(result, 'bar');
            default:
                return this.createTextCard(result);
        }
    }

    createSingleValueCard(result) {
        const key = Object.keys(result.data[0])[0];
        const value = result.data[0][key];
        
        return `
            <div class="dashboard-grid">
                <div class="card">
                    <div class="card-title">${result.description}</div>
                    <div class="single-value">${this.formatValue(value)}</div>
                </div>
            </div>
        `;
    }

    createTableCard(result) {
        const { data, columns } = result;
        
        let tableHTML = `
            <div class="card">
                <div class="card-title">${result.description || '查询结果'}</div>
                <table class="data-table">
                    <thead><tr>${columns.map(col => `<th>${col}</th>`).join('')}</tr></thead>
                    <tbody>
        `;

        data.slice(0, 100).forEach(row => {
            tableHTML += '<tr>';
            columns.forEach(col => {
                let value = row[col];
                if (value === null) value = '-';
                if (typeof value === 'object' && value instanceof Date) {
                    value = value.toLocaleString();
                }
                tableHTML += `<td>${value}</td>`;
            });
            tableHTML += '</tr>';
        });

        tableHTML += '</tbody></table>';
        
        if (data.length > 100) {
            tableHTML += `<div style="text-align: center; margin-top: 10px; color: #666;">
                显示前100条记录，共${data.length}条
            </div>`;
        }

        return tableHTML + '</div>';
    }

    createChartCard(result, chartType) {
        const chartId = `chart_${Date.now()}`;
        
        return `
            <div class="card">
                <div class="card-title">${result.description || '数据图表'}</div>
                <div class="chart-container">
                    <canvas id="${chartId}"></canvas>
                </div>
            </div>
        `;
    }

    createTextCard(result) {
        const value = Object.values(result.data[0])[0];
        
        return `
            <div class="card">
                <div class="card-title">${result.description || '查询结果'}</div>
                <p>${value}</p>
            </div>
        `;
    }

    generateDebugInfo(result) {
        const plan = result.query_plan;
        if (!plan) return '';

        return `
            <div class="card">
                <div class="card-title">🔍 查询分析</div>
                <div class="debug-info">
                    <div><strong>匹配的表:</strong> ${plan.primary_table}</div>
                    <div><strong>图表类型:</strong> ${plan.chart_type}</div>
                    <div><strong>SQL查询:</strong></div>
                    <pre style="background: white; padding: 10px; border-radius: 4px; overflow-x: auto;">
${result.sql_query}
                    </pre>
                    ${result.matched_tables ? `
                        <div><strong>表匹配分数:</strong></div>
                        <ul>
                            ${result.matched_tables.map(([table, score]) => 
                                `<li>${table}: ${score.toFixed(3)}</li>`
                            ).join('')}
                        </ul>
                    ` : ''}
                </div>
            </div>
        `;
    }

    initChart(result) {
        const ctx = document.getElementById(`chart_${Date.now()}`);
        if (!ctx) return;

        const { data, columns } = result;
        const labels = data.map(row => row[columns[0]]);
        const datasets = columns.slice(1).map((col, index) => ({
            label: col,
            data: data.map(row => row[col]),
            borderColor: this.getChartColor(index),
            backgroundColor: this.getChartColor(index, 0.2),
            tension: 0.4
        }));

        new Chart(ctx, {
            type: result.chart_type === 'line_chart' ? 'line' : 'bar',
            data: { labels, datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: result.description }
                }
            }
        });
    }

    getChartColor(index, alpha = 1) {
        const colors = [
            `rgba(102, 126, 234, ${alpha})`,
            `rgba(118, 75, 162, ${alpha})`,
            `rgba(255, 99, 132, ${alpha})`,
            `rgba(54, 162, 235, ${alpha})`,
            `rgba(255, 206, 86, ${alpha})`
        ];
        return colors[index % colors.length];
    }

    formatValue(value) {
        if (typeof value === 'number') {
            return value.toLocaleString();
        }
        return value;
    }

    showLoading() {
        document.getElementById('dashboardContainer').innerHTML = `
            <div class="card loading">
                <div>🧠 正在智能分析查询...</div>
            </div>
        `;
    }

    showError(message) {
        document.getElementById('dashboardContainer').innerHTML = `
            <div class="error">
                <strong>❌ 查询失败:</strong> ${message}
            </div>
        `;
    }
}

// 全局函数
function executeQuery() {
    if (typeof dashboard !== 'undefined') {
        dashboard.executeQuery();
    }
}

// 初始化
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new SmartDashboardManager();
    
    // 如果有预注入的数据，自动显示
    if (typeof window.queryData !== 'undefined') {
        setTimeout(() => {
            dashboard.renderDashboard(window.queryData);
        }, 100);
    }
});