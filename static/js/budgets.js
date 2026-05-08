// Runs after the page fully loads.
document.addEventListener("DOMContentLoaded", function () {

    // Gets all animated budget progress bars.
    const progressBars = document.querySelectorAll(".budget-progress-bar");

    // Animates each progress bar based on its percentage value.
    progressBars.forEach((bar) => {

        let width = parseFloat(bar.dataset.width);

        // Prevents invalid values from breaking the progress bar.
        if (isNaN(width)) {
            width = 0;
        }

        // Keeps the width between 0% and 100%.
        width = Math.max(0, Math.min(width, 100));

        // Starts animation from 0%.
        bar.style.width = "0%";

        // Smoothly expands the progress bar.
        setTimeout(() => {
            bar.style.width = width + "%";
        }, 100);
    });

    // -------------------
    // ADD BUDGET MONTH/YEAR LOGIC
    const monthSelect = document.getElementById("month");
    const yearSelect = document.getElementById("year");

    if (monthSelect && yearSelect) {
        const today = new Date();

        const currentMonth = today.getMonth() + 1;
        const currentYear = today.getFullYear();

        // List of month options used in the dropdown.
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

        // Updates available month options based on the selected year.
        function updateMonthOptions() {
            const selectedYear = parseInt(yearSelect.value);

            const currentSelectedMonth = parseInt(monthSelect.value);

            monthSelect.innerHTML = "";

            let allowedMonths = monthNames;

            // Prevents users from selecting past months in the current year.
            if (selectedYear === currentYear) {
                allowedMonths = monthNames.filter(month => month.value >= currentMonth);
            }

            // Rebuilds the month dropdown.
            allowedMonths.forEach(month => {

                const option = document.createElement("option");

                option.value = month.value;
                option.textContent = month.label;

                monthSelect.appendChild(option);
            });

            // Checks if the previously selected month is still valid.
            const stillValid = allowedMonths.some(
                month => month.value === currentSelectedMonth
            );

            if (stillValid) {
                monthSelect.value = String(currentSelectedMonth);

            } else if (allowedMonths.length > 0) {

                // Defaults to the first available month.
                monthSelect.value = String(allowedMonths[0].value);
            }
        }

        // Runs immediately when the page loads.
        updateMonthOptions();

        // Updates months whenever the year changes.
        yearSelect.addEventListener("change", updateMonthOptions);
    }

    // -------------------
    // EDIT BUDGET MODAL
    // -------------------
    const modalOverlay = document.getElementById("editBudgetModalOverlay");

    const editForm = document.getElementById("editBudgetForm");

    const closeBtn = document.getElementById("closeEditBudgetModal");

    const cancelBtn = document.getElementById("cancelEditBudget");

    const editButtons = document.querySelectorAll(".edit-budget-btn");

    // Edit form fields.
    const accountBookIdInput = document.getElementById("edit_budget_account_book_id");

    const accountBookNameInput = document.getElementById("edit_budget_account_book_name");

    const categoryInput = document.getElementById("edit_budget_category");

    const amountInput = document.getElementById("edit_budget_amount");

    const monthInput = document.getElementById("edit_budget_month");

    const yearInput = document.getElementById("edit_budget_year");

    // Stores original values to detect unsaved changes.
    const originalCategory = document.getElementById("original_budget_category");

    const originalAmount = document.getElementById("original_budget_amount");

    const originalMonth = document.getElementById("original_budget_month");

    const originalYear = document.getElementById("original_budget_year");

    // Opens the edit modal.
    function openModal() {

        if (!modalOverlay) return;

        modalOverlay.classList.remove("d-none");

        document.body.classList.add("modal-open");
    }

    // Checks whether the user changed any form values.
    function hasUnsavedChanges() {

        if (
            !editForm ||
            !categoryInput ||
            !amountInput ||
            !monthInput ||
            !yearInput ||
            !originalCategory ||
            !originalAmount ||
            !originalMonth ||
            !originalYear
        ) {
            return false;
        }

        return (
            categoryInput.value !== originalCategory.value ||
            amountInput.value !== originalAmount.value ||
            monthInput.value !== originalMonth.value ||
            yearInput.value !== originalYear.value
        );
    }

    // Closes the modal and optionally confirms unsaved changes.
    function closeModal(forceClose = false) {
        if (!modalOverlay || !editForm) return;

        // Warns the user before discarding unsaved changes.
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

    // Updates available months inside the edit modal.
    function updateEditMonthOptions() {
        if (!monthInput || !yearInput) return;

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

        // Prevents past months from appearing in the current year.
        if (selectedYear === currentYear) {
            allowedMonths = monthNames.filter(month => month.value >= currentMonth);
        }

        // Rebuilds the month dropdown.
        allowedMonths.forEach(month => {

            const option = document.createElement("option");

            option.value = month.value;
            option.textContent = month.label;

            monthInput.appendChild(option);
        });

        // Checks if the currently selected month is still valid.
        const stillValid = allowedMonths.some(
            month => month.value === currentSelectedMonth
        );

        if (stillValid) {
            monthInput.value = String(currentSelectedMonth);

        } else if (allowedMonths.length > 0) {

            monthInput.value = String(allowedMonths[0].value);
        }
    }

    // Opens the edit modal and fills it with budget data.
    editButtons.forEach((button) => {
        button.addEventListener("click", function () {

            if (
                !editForm ||
                !accountBookIdInput ||
                !accountBookNameInput ||
                !categoryInput ||
                !amountInput ||
                !monthInput ||
                !yearInput ||
                !originalCategory ||
                !originalAmount ||
                !originalMonth ||
                !originalYear
            ) {
                return;
            }

            // Gets budget data from the clicked button.
            const budgetId = this.dataset.budgetId;

            const accountBookId = this.dataset.accountBookId;

            const accountBookName = this.dataset.accountBookName;

            const category = this.dataset.category;

            const amount = this.dataset.amount;

            const month = this.dataset.month;

            const year = this.dataset.year;

            // Sets the correct edit route.
            editForm.action = `/budgets/${budgetId}/edit`;

            // Populates form fields.
            accountBookIdInput.value = accountBookId;

            accountBookNameInput.value = accountBookName;

            categoryInput.value = category;

            amountInput.value = amount;

            yearInput.value = year;

            updateEditMonthOptions();

            monthInput.value = month;

            // Saves original values for unsaved change detection.
            originalCategory.value = category;

            originalAmount.value = amount;

            originalMonth.value = month;

            originalYear.value = year;

            openModal();
        });
    });

    // Updates month options when the year changes.
    if (yearInput) {
        yearInput.addEventListener("change", updateEditMonthOptions);
    }

    // Close button.
    if (closeBtn) {
        closeBtn.addEventListener("click", function () {
            closeModal();
        });
    }

    // Cancel button.
    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            closeModal();
        });
    }

    // Prevents closing the modal when clicking outside the modal box.
    if (modalOverlay) {
        modalOverlay.addEventListener("click", function (event) {

            if (event.target === modalOverlay) {
                // Intentionally does nothing.
            }
        });
    }

    // Prevents the Escape key from closing the modal accidentally.
    document.addEventListener("keydown", function (event) {
        if (
            event.key === "Escape" &&
            modalOverlay &&
            !modalOverlay.classList.contains("d-none")
        ) {
            event.preventDefault();
        }
    });
});