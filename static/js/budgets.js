document.addEventListener("DOMContentLoaded", function () {
    const progressBars = document.querySelectorAll(".budget-progress-bar");

    progressBars.forEach((bar) => {
        let width = parseFloat(bar.dataset.width);

        if (isNaN(width)) {
            width = 0;
        }

        width = Math.max(0, Math.min(width, 100));

        bar.style.width = "0%";

        setTimeout(() => {
            bar.style.width = width + "%";
        }, 100);
    });

    const monthSelect = document.getElementById("month");
    const yearSelect = document.getElementById("year");

    if (monthSelect && yearSelect) {
        const today = new Date();
        const currentMonth = today.getMonth() + 1;
        const currentYear = today.getFullYear();

        const monthNames = [
            { value: 1, label: "January" },
            { value: 2, label: "February" },
            { value: 3, label: "March" },
            { value: 4, label: "April" },
            { value: 5, label: "May" },
            { value: 6, label: "June" },
            { value: 7, label: "July" },
            { value: 8, label: "August" },
            { value: 9, label: "September" },
            { value: 10, label: "October" },
            { value: 11, label: "November" },
            { value: 12, label: "December" }
        ];

        function updateMonthOptions() {
            const selectedYear = parseInt(yearSelect.value);
            const currentSelectedMonth = parseInt(monthSelect.value);

            monthSelect.innerHTML = "";

            let allowedMonths = monthNames;

            if (selectedYear === currentYear) {
                allowedMonths = monthNames.filter(month => month.value >= currentMonth);
            }

            allowedMonths.forEach(month => {
                const option = document.createElement("option");
                option.value = month.value;
                option.textContent = month.label;
                monthSelect.appendChild(option);
            });

            const stillValid = allowedMonths.some(month => month.value === currentSelectedMonth);

            if (stillValid) {
                monthSelect.value = currentSelectedMonth;
            } else {
                monthSelect.value = String(allowedMonths[0].value);
            }
        }

        updateMonthOptions();
        yearSelect.addEventListener("change", updateMonthOptions);
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const progressBars = document.querySelectorAll(".budget-progress-bar");

    progressBars.forEach((bar) => {
        let width = parseFloat(bar.dataset.width);

        if (isNaN(width)) {
            width = 0;
        }

        width = Math.max(0, Math.min(width, 100));

        bar.style.width = "0%";

        setTimeout(() => {
            bar.style.width = width + "%";
        }, 100);
    });

    const monthSelect = document.getElementById("month");
    const yearSelect = document.getElementById("year");

    if (monthSelect && yearSelect) {
        const today = new Date();
        const currentMonth = today.getMonth() + 1;
        const currentYear = today.getFullYear();

        const monthNames = [
            { value: 1, label: "January" },
            { value: 2, label: "February" },
            { value: 3, label: "March" },
            { value: 4, label: "April" },
            { value: 5, label: "May" },
            { value: 6, label: "June" },
            { value: 7, label: "July" },
            { value: 8, label: "August" },
            { value: 9, label: "September" },
            { value: 10, label: "October" },
            { value: 11, label: "November" },
            { value: 12, label: "December" }
        ];

        function updateMonthOptions() {
            const selectedYear = parseInt(yearSelect.value);
            const currentSelectedMonth = parseInt(monthSelect.value);

            monthSelect.innerHTML = "";

            let allowedMonths = monthNames;

            if (selectedYear === currentYear) {
                allowedMonths = monthNames.filter(month => month.value >= currentMonth);
            }

            allowedMonths.forEach(month => {
                const option = document.createElement("option");
                option.value = month.value;
                option.textContent = month.label;
                monthSelect.appendChild(option);
            });

            const stillValid = allowedMonths.some(month => month.value === currentSelectedMonth);

            if (stillValid) {
                monthSelect.value = currentSelectedMonth;
            } else {
                monthSelect.value = String(allowedMonths[0].value);
            }
        }

        updateMonthOptions();
        yearSelect.addEventListener("change", updateMonthOptions);
    }

    const modalOverlay = document.getElementById("editBudgetModalOverlay");
    const editForm = document.getElementById("editBudgetForm");
    const closeBtn = document.getElementById("closeEditBudgetModal");
    const cancelBtn = document.getElementById("cancelEditBudget");
    const editButtons = document.querySelectorAll(".edit-budget-btn");

    const accountBookIdInput = document.getElementById("edit_budget_account_book_id");
    const accountBookNameInput = document.getElementById("edit_budget_account_book_name");
    const categoryInput = document.getElementById("edit_budget_category");
    const amountInput = document.getElementById("edit_budget_amount");
    const monthInput = document.getElementById("edit_budget_month");
    const yearInput = document.getElementById("edit_budget_year");

    const originalCategory = document.getElementById("original_budget_category");
    const originalAmount = document.getElementById("original_budget_amount");
    const originalMonth = document.getElementById("original_budget_month");
    const originalYear = document.getElementById("original_budget_year");

    function openModal() {
        modalOverlay.classList.remove("d-none");
        document.body.classList.add("modal-open");
    }

    function closeModal(forceClose = false) {
        if (!forceClose && hasUnsavedChanges()) {
            const discard = confirm("Discard changes?");
            if (!discard) {
                return;
            }
        }

        modalOverlay.classList.add("d-none");
        document.body.classList.remove("modal-open");
        editForm.reset();
    }

    function hasUnsavedChanges() {
        if (!editForm) return false;

        return (
            categoryInput.value !== originalCategory.value ||
            amountInput.value !== originalAmount.value ||
            monthInput.value !== originalMonth.value ||
            yearInput.value !== originalYear.value
        );
    }

    function updateEditMonthOptions() {
        const today = new Date();
        const currentMonth = today.getMonth() + 1;
        const currentYear = today.getFullYear();
        const selectedYear = parseInt(yearInput.value);
        const currentSelectedMonth = parseInt(monthInput.value);

        const monthNames = [
            { value: 1, label: "January" },
            { value: 2, label: "February" },
            { value: 3, label: "March" },
            { value: 4, label: "April" },
            { value: 5, label: "May" },
            { value: 6, label: "June" },
            { value: 7, label: "July" },
            { value: 8, label: "August" },
            { value: 9, label: "September" },
            { value: 10, label: "October" },
            { value: 11, label: "November" },
            { value: 12, label: "December" }
        ];

        monthInput.innerHTML = "";

        let allowedMonths = monthNames;
        if (selectedYear === currentYear) {
            allowedMonths = monthNames.filter(month => month.value >= currentMonth);
        }

        allowedMonths.forEach(month => {
            const option = document.createElement("option");
            option.value = month.value;
            option.textContent = month.label;
            monthInput.appendChild(option);
        });

        const stillValid = allowedMonths.some(month => month.value === currentSelectedMonth);

        if (stillValid) {
            monthInput.value = String(currentSelectedMonth);
        } else {
            monthInput.value = String(allowedMonths[0].value);
        }
    }

    editButtons.forEach((button) => {
        button.addEventListener("click", function () {
            const budgetId = this.dataset.budgetId;
            const accountBookId = this.dataset.accountBookId;
            const accountBookName = this.dataset.accountBookName;
            const category = this.dataset.category;
            const amount = this.dataset.amount;
            const month = this.dataset.month;
            const year = this.dataset.year;

            editForm.action = `/budgets/${budgetId}/edit`;

            accountBookIdInput.value = accountBookId;
            accountBookNameInput.value = accountBookName;
            categoryInput.value = category;
            amountInput.value = amount;
            yearInput.value = year;

            updateEditMonthOptions();
            monthInput.value = month;

            originalCategory.value = category;
            originalAmount.value = amount;
            originalMonth.value = month;
            originalYear.value = year;

            openModal();
        });
    });

    if (yearInput) {
        yearInput.addEventListener("change", updateEditMonthOptions);
    }

    if (closeBtn) {
        closeBtn.addEventListener("click", function () {
            closeModal();
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            closeModal();
        });
    }

    if (modalOverlay) {
        modalOverlay.addEventListener("click", function (event) {
            if (event.target === modalOverlay) {
                // intentionally do nothing so clicking outside does NOT close
            }
        });
    }

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modalOverlay && !modalOverlay.classList.contains("d-none")) {
            event.preventDefault();
        }
    });
});