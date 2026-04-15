function setupMonthDropdown(config) {
    var dropdownButton = document.getElementById(config.buttonId);
    var dropdownMenu = document.getElementById(config.menuId);
    var selectAllBtn = document.getElementById(config.selectAllId);
    var clearAllBtn = document.getElementById(config.clearAllId);
    var allMonthsCheckbox = document.getElementById(config.allCheckboxId);
    var monthCheckboxes = document.querySelectorAll(config.monthCheckboxSelector);
    var yearSelect = document.getElementById(config.yearSelectId);
    var monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

    function getCheckedCount() {
        var checkedCount = 0;
        monthCheckboxes.forEach(function (checkbox) {
            if (checkbox.checked) checkedCount++;
        });
        return checkedCount;
    }

    function syncAllCheckbox() {
        if (allMonthsCheckbox) {
            allMonthsCheckbox.checked = getCheckedCount() === 12;
        }
    }

    function updateButtonText() {
        if (!dropdownButton) return;

        if (yearSelect && yearSelect.value === "all") {
            dropdownButton.textContent = "All Months";
            return;
        }

        var checked = [];
        monthCheckboxes.forEach(function (checkbox) {
            if (checkbox.checked) checked.push(parseInt(checkbox.value, 10));
        });

        if (checked.length === 12 || checked.length === 0) {
            dropdownButton.textContent = "All Months";
        } else if (checked.length === 1) {
            dropdownButton.textContent = monthNames[checked[0] - 1];
        } else {
            dropdownButton.textContent = checked.length + " Months Selected";
        }
    }

    if (dropdownButton && dropdownMenu) {
        dropdownButton.addEventListener("click", function (e) {
            if (dropdownButton.disabled) return;
            e.stopPropagation();
            dropdownMenu.classList.toggle("show");
        });

        document.addEventListener("click", function (e) {
            if (!dropdownMenu.contains(e.target) && !dropdownButton.contains(e.target)) {
                dropdownMenu.classList.remove("show");
            }
        });
    }

    if (selectAllBtn) {
        selectAllBtn.addEventListener("click", function () {
            monthCheckboxes.forEach(function (checkbox) {
                checkbox.checked = true;
            });
            syncAllCheckbox();
            updateButtonText();
        });
    }

    if (clearAllBtn) {
        clearAllBtn.addEventListener("click", function () {
            monthCheckboxes.forEach(function (checkbox) {
                checkbox.checked = false;
            });
            syncAllCheckbox();
            updateButtonText();
        });
    }

    if (allMonthsCheckbox) {
        allMonthsCheckbox.addEventListener("change", function () {
            monthCheckboxes.forEach(function (checkbox) {
                checkbox.checked = allMonthsCheckbox.checked;
            });
            updateButtonText();
        });
    }

    monthCheckboxes.forEach(function (checkbox) {
        checkbox.addEventListener("change", function () {
            syncAllCheckbox();
            updateButtonText();
        });
    });

    if (yearSelect) {
        yearSelect.addEventListener("change", function () {
            if (yearSelect.value === "all") {
                monthCheckboxes.forEach(function (checkbox) {
                    checkbox.checked = true;
                });
                syncAllCheckbox();

                if (dropdownMenu) dropdownMenu.classList.remove("show");
                if (dropdownButton) dropdownButton.disabled = true;
            } else {
                if (dropdownButton) dropdownButton.disabled = false;
            }

            updateButtonText();
        });
    }

    syncAllCheckbox();
    updateButtonText();
}

document.addEventListener("DOMContentLoaded", function () {
    setupMonthDropdown({
        buttonId: "monthDropdownButton",
        menuId: "monthDropdownMenu",
        selectAllId: "selectAllMonths",
        clearAllId: "clearAllMonths",
        allCheckboxId: "allMonthsCheckbox",
        monthCheckboxSelector: ".month-checkbox",
        yearSelectId: "year"
    });

    var labels = JSON.parse(document.getElementById("chart-labels").textContent);
    var incomeData = JSON.parse(document.getElementById("chart-income-data").textContent);
    var expenseData = JSON.parse(document.getElementById("chart-expense-data").textContent);

    var incomeCategoryLabels = JSON.parse(document.getElementById("income-category-labels").textContent);
    var incomeCategoryData = JSON.parse(document.getElementById("income-category-data").textContent);
    var expenseCategoryLabels = JSON.parse(document.getElementById("expense-category-labels").textContent);
    var expenseCategoryData = JSON.parse(document.getElementById("expense-category-data").textContent);

    var canvas = document.getElementById("incomeExpenseChart");
    var chartTypeSelect = document.getElementById("dashboardChartType");

    if (!canvas) return;

    var ctx = canvas.getContext("2d");
    var currentChart;

    function pieTooltipLabel(context) {
        const data = context.dataset.data || [];
        const total = data.reduce((sum, value) => sum + Number(value || 0), 0);
        const value = Number(context.raw || 0);
        const percent = total > 0 ? ((value / total) * 100).toFixed(1) : "0.0";
        return `${context.label}: $${value.toFixed(2)} (${percent}%)`;
    }

    function buildChartConfig(chartType) {
        if (chartType === "line") {
            return {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: "Income",
                            data: incomeData,
                            borderColor: "rgba(34, 197, 94, 1)",
                            backgroundColor: "rgba(34, 197, 94, 0.15)",
                            borderWidth: 3,
                            tension: 0.3,
                            fill: false,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        },
                        {
                            label: "Expenses",
                            data: expenseData,
                            borderColor: "rgba(239, 68, 68, 1)",
                            backgroundColor: "rgba(239, 68, 68, 0.15)",
                            borderWidth: 3,
                            tension: 0.3,
                            fill: false,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 800 },
                    plugins: {
                        legend: { position: "top" },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ": $" + Number(context.raw).toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return "$" + value;
                                }
                            }
                        }
                    }
                }
            };
        }

        if (chartType === "incomePie") {
            return {
                type: "pie",
                data: {
                    labels: incomeCategoryLabels,
                    datasets: [
                        {
                            label: "Income Categories",
                            data: incomeCategoryData
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 800 },
                    plugins: {
                        legend: { position: "top" },
                        tooltip: {
                            callbacks: {
                                label: pieTooltipLabel
                            }
                        }
                    }
                }
            };
        }

        if (chartType === "expensePie") {
            return {
                type: "pie",
                data: {
                    labels: expenseCategoryLabels,
                    datasets: [
                        {
                            label: "Expense Categories",
                            data: expenseCategoryData
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 800 },
                    plugins: {
                        legend: { position: "top" },
                        tooltip: {
                            callbacks: {
                                label: pieTooltipLabel
                            }
                        }
                    }
                }
            };
        }

        return {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Income",
                        data: incomeData,
                        backgroundColor: "rgba(34, 197, 94, 0.7)",
                        borderColor: "rgba(34, 197, 94, 1)",
                        borderWidth: 1,
                        borderRadius: 6
                    },
                    {
                        label: "Expenses",
                        data: expenseData,
                        backgroundColor: "rgba(239, 68, 68, 0.7)",
                        borderColor: "rgba(239, 68, 68, 1)",
                        borderWidth: 1,
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 800 },
                plugins: {
                    legend: { position: "top" },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ": $" + Number(context.raw).toFixed(2);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return "$" + value;
                            }
                        }
                    }
                }
            }
        };
    }

    function renderChart(chartType) {
        if (currentChart) currentChart.destroy();
        currentChart = new Chart(ctx, buildChartConfig(chartType));
    }

    const dashboardChartStorageKey = "dashboardChartType";
    const savedDashboardChartType = localStorage.getItem(dashboardChartStorageKey) || "bar";

    if (chartTypeSelect) {
        chartTypeSelect.value = savedDashboardChartType;
    }

    renderChart(savedDashboardChartType);

    if (chartTypeSelect) {
        chartTypeSelect.addEventListener("change", function () {
            localStorage.setItem(dashboardChartStorageKey, chartTypeSelect.value);
            renderChart(chartTypeSelect.value);
        });
    }
});