// Creates a reusable month dropdown component for chart filtering.
function setupMonthDropdown(config) {

    // Gets all dropdown elements using the provided configuration IDs.
    var dropdownButton = document.getElementById(config.buttonId);
    var dropdownMenu = document.getElementById(config.menuId);

    var selectAllBtn = document.getElementById(config.selectAllId);
    var clearAllBtn = document.getElementById(config.clearAllId);

    var allMonthsCheckbox = document.getElementById(config.allCheckboxId);

    var monthCheckboxes = document.querySelectorAll(config.monthCheckboxSelector);

    var yearSelect = document.getElementById(config.yearSelectId);

    // Short month labels used in the dropdown button.
    var monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

    // Counts how many month checkboxes are selected.
    function getCheckedCount() {

        var checkedCount = 0;

        monthCheckboxes.forEach(function (checkbox) {

            if (checkbox.checked) checkedCount++;
        });

        return checkedCount;
    }

    // Keeps the "All Months" checkbox synced with the individual month checkboxes.
    function syncAllCheckbox() {

        if (allMonthsCheckbox) {

            allMonthsCheckbox.checked = getCheckedCount() === 12;
        }
    }

    // Updates the dropdown button text based on selected months.
    function updateButtonText() {

        if (!dropdownButton) return;

        // Shows "All Months" if all years is selected.
        if (yearSelect && yearSelect.value === "all") {

            dropdownButton.textContent = "All Months";

            return;
        }

        var checked = [];

        monthCheckboxes.forEach(function (checkbox) {

            if (checkbox.checked) {
                checked.push(parseInt(checkbox.value, 10));
            }
        });

        // Updates the button label depending on how many months are selected.
        if (checked.length === 12 || checked.length === 0) {

            dropdownButton.textContent = "All Months";

        } else if (checked.length === 1) {

            dropdownButton.textContent = monthNames[checked[0] - 1];

        } else {

            dropdownButton.textContent = checked.length + " Months Selected";
        }
    }

    // -------------------
    // DROPDOWN OPEN/CLOSE
    // -------------------
    if (dropdownButton && dropdownMenu) {

        dropdownButton.addEventListener("click", function (e) {

            if (dropdownButton.disabled) return;

            e.stopPropagation();

            dropdownMenu.classList.toggle("show");
        });

        // Closes the dropdown when clicking outside of it.
        document.addEventListener("click", function (e) {

            if (
                !dropdownMenu.contains(e.target) &&
                !dropdownButton.contains(e.target)
            ) {
                dropdownMenu.classList.remove("show");
            }
        });
    }

    // -------------------
    // SELECT ALL MONTHS
    // -------------------
    if (selectAllBtn) {

        selectAllBtn.addEventListener("click", function () {

            monthCheckboxes.forEach(function (checkbox) {
                checkbox.checked = true;
            });

            syncAllCheckbox();

            updateButtonText();
        });
    }

    // -------------------
    // CLEAR ALL MONTHS
    // -------------------
    if (clearAllBtn) {

        clearAllBtn.addEventListener("click", function () {

            monthCheckboxes.forEach(function (checkbox) {
                checkbox.checked = false;
            });

            syncAllCheckbox();

            updateButtonText();
        });
    }

    // -------------------
    // ALL MONTHS CHECKBOX
    // -------------------
    if (allMonthsCheckbox) {

        allMonthsCheckbox.addEventListener("change", function () {

            // Selects or deselects every month checkbox.
            monthCheckboxes.forEach(function (checkbox) {

                checkbox.checked = allMonthsCheckbox.checked;
            });

            updateButtonText();
        });
    }

    // -------------------
    // INDIVIDUAL MONTH CHECKBOXES
    // -------------------
    monthCheckboxes.forEach(function (checkbox) {

        checkbox.addEventListener("change", function () {

            syncAllCheckbox();

            updateButtonText();
        });
    });

    // -------------------
    // YEAR DROPDOWN
    // -------------------
    if (yearSelect) {

        yearSelect.addEventListener("change", function () {

            // Automatically selects all months when "All Years" is selected.
            if (yearSelect.value === "all") {

                monthCheckboxes.forEach(function (checkbox) {
                    checkbox.checked = true;
                });

                syncAllCheckbox();

                // Closes and disables the dropdown.
                if (dropdownMenu) dropdownMenu.classList.remove("show");

                if (dropdownButton) dropdownButton.disabled = true;

            } else {

                // Re-enables the dropdown for normal year selection.
                if (dropdownButton) dropdownButton.disabled = false;
            }

            updateButtonText();
        });
    }

    // Runs initial setup.
    syncAllCheckbox();

    updateButtonText();
}

// Runs after the page fully loads.
document.addEventListener("DOMContentLoaded", function () {

    // Initializes the reusable month dropdown.
    setupMonthDropdown({
        buttonId: "monthDropdownButton",
        menuId: "monthDropdownMenu",
        selectAllId: "selectAllMonths",
        clearAllId: "clearAllMonths",
        allCheckboxId: "allMonthsCheckbox",
        monthCheckboxSelector: ".month-checkbox",
        yearSelectId: "year"
    });

    // -------------------
    // CHART DATA
    // -------------------

    // Loads chart data passed from Flask templates.
    var labels = JSON.parse(document.getElementById("chart-labels").textContent);

    var incomeData = JSON.parse(document.getElementById("chart-income-data").textContent);

    var expenseData = JSON.parse(document.getElementById("chart-expense-data").textContent);

    var incomeCategoryLabels = JSON.parse(document.getElementById("income-category-labels").textContent);

    var incomeCategoryData = JSON.parse(document.getElementById("income-category-data").textContent);

    var expenseCategoryLabels = JSON.parse(document.getElementById("expense-category-labels").textContent);

    var expenseCategoryData = JSON.parse(document.getElementById("expense-category-data").textContent);


    // Gets chart canvas and chart type selector.
    var canvas = document.getElementById("incomeExpenseChart");

    var chartTypeSelect = document.getElementById("dashboardChartType");

    if (!canvas) return;

    var ctx = canvas.getContext("2d");

    var currentChart;

    // Creates percentage tooltips for pie charts.
    function pieTooltipLabel(context) {
        const data = context.dataset.data || [];

        const total = data.reduce((sum, value) => sum + Number(value || 0), 0);

        const value = Number(context.raw || 0);

        const percent = total > 0
            ? ((value / total) * 100).toFixed(1)
            : "0.0";

        return `${context.label}: $${value.toFixed(2)} (${percent}%)`;
    }

    // Builds different chart configurations depending on chart type.
    function buildChartConfig(chartType) {

        // -------------------
        // LINE CHART
        // -------------------
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

        // -------------------
        // INCOME PIE CHART
        // -------------------
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

        // -------------------
        // EXPENSE PIE CHART
        // -------------------
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

        // -------------------
        // DEFAULT BAR CHART
        // -------------------
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

    // Renders the selected chart type.
    function renderChart(chartType) {

        // Destroys the previous chart before creating a new one.
        if (currentChart) currentChart.destroy();

        currentChart = new Chart(ctx, buildChartConfig(chartType));
    }

    // -------------------
    // CHART TYPE PERSISTENCE
    // -------------------

    // Saves the selected chart type using localStorage.
    const dashboardChartStorageKey = "dashboardChartType";

    const savedDashboardChartType =
        localStorage.getItem(dashboardChartStorageKey) || "bar";

    // Restores the previously selected chart type.
    if (chartTypeSelect) {
        chartTypeSelect.value = savedDashboardChartType;
    }

    renderChart(savedDashboardChartType);

    // Updates the chart and saves the new chart type.
    if (chartTypeSelect) {

        chartTypeSelect.addEventListener("change", function () {

            localStorage.setItem(
                dashboardChartStorageKey,
                chartTypeSelect.value
            );

            renderChart(chartTypeSelect.value);
        });
    }
});