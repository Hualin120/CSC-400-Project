function openExportModal() {
    document.getElementById('exportModal').style.display = 'block';
}

function closeExportModal() {
    document.getElementById('exportModal').style.display = 'none';
}

function openImportModal() {
    document.getElementById('importModal').style.display = 'block';
}

function closeImportModal() {
    document.getElementById('importModal').style.display = 'none';
}

function openCreateBookModal() {
    document.getElementById('createBookModal').style.display = 'block';
}

function closeCreateBookModal() {
    document.getElementById('createBookModal').style.display = 'none';
}

function getCategoriesByType(type) {
    const incomeCategories = [
        'Salary',
        'Part Time',
        'Freelance',
        'Allowance',
        'Refund',
        'Gift',
        'Other'
    ];

    const expenseCategories = [
        'Housing',
        'Utilities',
        'Groceries',
        'Food',
        'Transportation',
        'Insurance',
        'Subscriptions',
        'Entertainment',
        'Shopping',
        'Medical',
        'Travel',
        'Other'
    ];

    return type === 'income' ? incomeCategories : expenseCategories;
}

function populateModalCategoryOptions(type, selectedCategory) {
    const modalCategory = document.getElementById('modalCategory');
    const categories = getCategoriesByType(type);

    modalCategory.innerHTML = '';

    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;

        if (category === selectedCategory) {
            option.selected = true;
        }

        modalCategory.appendChild(option);
    });
}

let transactionModalInitialState = null;
let transactionModalDirty = false;

function getTransactionModalState() {
    return {
        type: document.getElementById('modalTransactionType').value,
        amount: document.getElementById('modalAmount').value,
        category: document.getElementById('modalCategory').value,
        description: document.getElementById('modalDescription').value,
        date: document.getElementById('modalDate').value
    };
}

function updateTransactionModalDirtyState() {
    if (!transactionModalInitialState) {
        transactionModalDirty = false;
        return;
    }

    const currentState = getTransactionModalState();

    transactionModalDirty =
        currentState.type !== transactionModalInitialState.type ||
        currentState.amount !== transactionModalInitialState.amount ||
        currentState.category !== transactionModalInitialState.category ||
        currentState.description !== transactionModalInitialState.description ||
        currentState.date !== transactionModalInitialState.date;
}

function attemptCloseTransactionModal() {
    updateTransactionModalDirtyState();

    if (transactionModalDirty) {
        const confirmed = confirm('Discard your unsaved changes?');
        if (!confirmed) return;
    }

    closeTransactionModal(true);
}

function openTransactionModal(button) {
    const type = button.dataset.type;
    const id = button.dataset.id;
    const category = button.dataset.category;
    const description = button.dataset.description;
    const date = button.dataset.date;
    const amount = button.dataset.amount;

    document.getElementById('modalTransactionType').value = type;
    document.getElementById('modalTransactionId').value = id;
    document.getElementById('modalTypeDisplay').value = type.charAt(0).toUpperCase() + type.slice(1);
    document.getElementById('modalAmount').value = amount;
    document.getElementById('modalDescription').value = description;
    document.getElementById('modalDate').value = date;

    populateModalCategoryOptions(type, category);

    document.getElementById('editTransactionForm').action = `/edit-transaction/${type}/${id}`;
    document.getElementById('transactionModal').style.display = 'block';

    transactionModalInitialState = getTransactionModalState();
    transactionModalDirty = false;
}

function closeTransactionModal(forceClose = false) {
    if (!forceClose) {
        attemptCloseTransactionModal();
        return;
    }

    document.getElementById('transactionModal').style.display = 'none';
    transactionModalInitialState = null;
    transactionModalDirty = false;
}

function confirmDeleteTransaction() {
    const type = document.getElementById('modalTransactionType').value;
    const id = document.getElementById('modalTransactionId').value;

    const confirmed = confirm('Are you sure you want to delete this transaction? This cannot be undone.');
    if (!confirmed) return;

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/delete_transaction/${type}/${id}`;
    document.body.appendChild(form);
    form.submit();
}

function selectAll(select) {
    const checkboxes = document.querySelectorAll('#exportForm input[name="book_ids"]');
    checkboxes.forEach(cb => cb.checked = select);
}

function updateCategoryOptions() {
    const typeSelect = document.querySelector('select[name="type"]');
    const categorySelect = document.querySelector('select[name="category"]');

    if (!typeSelect || !categorySelect) return;

    const selectedType = typeSelect.value;

    const incomeCategories = [
        { value: 'Salary', label: 'Salary' },
        { value: 'Part Time', label: 'Part Time' },
        { value: 'Freelance', label: 'Freelance' },
        { value: 'Allowance', label: 'Allowance' },
        { value: 'Refund', label: 'Refund' },
        { value: 'Gift', label: 'Gift' },
        { value: 'Other', label: 'Other' }
    ];

    const expenseCategories = [
        { value: 'Housing', label: 'Housing' },
        { value: 'Utilities', label: 'Utilities' },
        { value: 'Groceries', label: 'Groceries' },
        { value: 'Food', label: 'Food' },
        { value: 'Transportation', label: 'Transportation' },
        { value: 'Insurance', label: 'Insurance' },
        { value: 'Subscriptions', label: 'Subscriptions' },
        { value: 'Entertainment', label: 'Entertainment' },
        { value: 'Shopping', label: 'Shopping' },
        { value: 'Medical', label: 'Medical' },
        { value: 'Travel', label: 'Travel' },
        { value: 'Other', label: 'Other' }
    ];

    const categories = selectedType === 'income' ? incomeCategories : expenseCategories;

    categorySelect.innerHTML = '';

    categories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.value;
        option.textContent = cat.label;
        categorySelect.appendChild(option);
    });
}

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

const tableSortDirections = {};

function parseDate(dateStr) {
    const parts = dateStr.split('/');
    return new Date(parts[2], parts[0] - 1, parts[1]);
}

function parseAmount(amountStr) {
    return parseFloat(amountStr.replace(/[$,]/g, '')) || 0;
}

function sortTable(tableId, columnIndex, type) {
    const table = document.getElementById(tableId);
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    const sortKey = `${tableId}-${columnIndex}`;
    tableSortDirections[sortKey] = !tableSortDirections[sortKey];
    const ascending = tableSortDirections[sortKey];

    rows.sort((a, b) => {
        let aText = a.cells[columnIndex].innerText.trim();
        let bText = b.cells[columnIndex].innerText.trim();
        let comparison = 0;

        if (type === 'date') {
            comparison = parseDate(aText) - parseDate(bText);
        } else if (type === 'amount') {
            comparison = parseAmount(aText) - parseAmount(bText);
        } else {
            comparison = aText.localeCompare(bText);
        }

        return ascending ? comparison : -comparison;
    });

    rows.forEach(row => tbody.appendChild(row));
    updateSortArrows(table, columnIndex, ascending);
}

function updateSortArrows(table, activeColumn, ascending) {
    const headers = table.querySelectorAll('th');

    headers.forEach((th, index) => {
        const up = th.querySelector('.arrow-up');
        const down = th.querySelector('.arrow-down');

        if (!up || !down) return;

        if (index === activeColumn) {
            if (ascending) {
                up.style.opacity = '1';
                down.style.opacity = '0.3';
            } else {
                up.style.opacity = '0.3';
                down.style.opacity = '1';
            }
        } else {
            up.style.opacity = '0.5';
            down.style.opacity = '0.5';
        }
    });
}

document.addEventListener("DOMContentLoaded", function() {
    const typeSelect = document.querySelector('select[name="type"]');
    if (typeSelect) {
        updateCategoryOptions();
        typeSelect.addEventListener('change', updateCategoryOptions);
    }

    setupMonthDropdown({
        buttonId: "transactionMonthDropdownButton",
        menuId: "transactionMonthDropdownMenu",
        selectAllId: "transactionSelectAllMonths",
        clearAllId: "transactionClearAllMonths",
        allCheckboxId: "transactionAllMonthsCheckbox",
        monthCheckboxSelector: ".transaction-month-checkbox",
        yearSelectId: "year"
    });

    const closeTransactionModalBtn = document.getElementById('closeTransactionModalBtn');
    if (closeTransactionModalBtn) {
        closeTransactionModalBtn.addEventListener('click', function () {
            attemptCloseTransactionModal();
        });
    }

    const cancelTransactionBtn = document.getElementById('cancelTransactionBtn');
    if (cancelTransactionBtn) {
        cancelTransactionBtn.addEventListener('click', function () {
            attemptCloseTransactionModal();
        });
    }

    const deleteTransactionBtn = document.getElementById('deleteTransactionBtn');
    if (deleteTransactionBtn) {
        deleteTransactionBtn.addEventListener('click', function () {
            confirmDeleteTransaction();
        });
    }

    const modalAmount = document.getElementById('modalAmount');
    const modalCategory = document.getElementById('modalCategory');
    const modalDescription = document.getElementById('modalDescription');
    const modalDate = document.getElementById('modalDate');

    [modalAmount, modalCategory, modalDescription, modalDate].forEach(field => {
        if (field) {
            field.addEventListener('input', updateTransactionModalDirtyState);
            field.addEventListener('change', updateTransactionModalDirtyState);
        }
    });

    const editTransactionForm = document.getElementById('editTransactionForm');
    if (editTransactionForm) {
        editTransactionForm.addEventListener('submit', function () {
            transactionModalDirty = false;
        });
    }

    var labels = JSON.parse(document.getElementById("book-chart-labels").textContent);
    var incomeData = JSON.parse(document.getElementById("book-chart-income-data").textContent);
    var expenseData = JSON.parse(document.getElementById("book-chart-expense-data").textContent);

    var incomeCategoryLabels = JSON.parse(document.getElementById("income-category-labels").textContent);
    var incomeCategoryData = JSON.parse(document.getElementById("income-category-data").textContent);
    var expenseCategoryLabels = JSON.parse(document.getElementById("expense-category-labels").textContent);
    var expenseCategoryData = JSON.parse(document.getElementById("expense-category-data").textContent);

    var canvas = document.getElementById("bookIncomeExpenseChart");
    var chartTypeSelect = document.getElementById("transactionChartType");

    if (!canvas) return;

    var ctx = canvas.getContext("2d");
    var currentChart;

    function pieTooltipLabel(context) {
        const data = context.dataset.data || [];
        const total = data.reduce((sum, value) => sum + Number(value || 0), 0);
        const value = Number(context.raw || 0);
        const percent = total > 0 ? ((value / total) * 100).toFixed(1) : "0.0";
        const word = value === 1 ? "transaction" : "transactions";
        return `${context.label}: ${value} ${word} (${percent}%)`;
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

    const transactionChartStorageKey = "transactionChartType";
    const savedTransactionChartType = localStorage.getItem(transactionChartStorageKey) || "bar";

    if (chartTypeSelect) {
        chartTypeSelect.value = savedTransactionChartType;
    }

    renderChart(savedTransactionChartType);

    if (chartTypeSelect) {
        chartTypeSelect.addEventListener("change", function () {
            localStorage.setItem(transactionChartStorageKey, chartTypeSelect.value);
            renderChart(chartTypeSelect.value);
        });
    }
});