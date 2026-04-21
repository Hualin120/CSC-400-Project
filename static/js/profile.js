document.addEventListener("DOMContentLoaded", function () {

    const displayMode = document.getElementById("displayMode");
    const editForm = document.getElementById("editForm");
    const editBtn = document.getElementById("editBtn");
    const cancelBtn = document.getElementById("cancelBtn");
    const avatarWrapper = document.getElementById("avatarWrapper");
    const avatarInput = document.getElementById("avatarInput");
    const avatarImg = document.getElementById("userAvatar");

    let originalFormData = new FormData(editForm);

    // ===== ENTER EDIT MODE =====
    if (editBtn) {
        editBtn.addEventListener("click", function () {
            displayMode.style.display = "none";
            editForm.style.display = "block";

            // Save original state when entering edit mode
            originalFormData = new FormData(editForm);
        });
    }

    // ===== CANCEL WITH CONFIRM =====
    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {

            const currentFormData = new FormData(editForm);

            let hasChanges = false;

            for (let [key, value] of currentFormData.entries()) {
                if (originalFormData.get(key) !== value) {
                    hasChanges = true;
                    break;
                }
            }

            if (hasChanges) {
                const confirmLeave = confirm("Are you sure you want to discard your changes?");
                if (!confirmLeave) return;
            }

            displayMode.style.display = "block";
            editForm.style.display = "none";
            editForm.reset();
        });
    }

    // ===== AVATAR CLICK =====
    if (avatarWrapper) {
        avatarWrapper.addEventListener("click", function () {
            avatarInput.click();
        });
    }

    // ===== AVATAR UPLOAD =====
    if (avatarInput) {
        avatarInput.addEventListener("change", function (e) {
            const file = e.target.files[0];
            if (!file) return;

            const allowedTypes = ["image/png", "image/jpeg", "image/jpg", "image/gif"];
            if (!allowedTypes.includes(file.type)) {
                alert("Only PNG, JPEG, and GIF images are allowed.");
                return;
            }

            if (file.size > 2 * 1024 * 1024) {
                alert("Image must be under 2MB.");
                return;
            }

            const formData = new FormData();
            formData.append("avatar", file);

            fetch("/edit_profile", {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    if (avatarImg) {
                        avatarImg.src = avatarImg.src.split("?")[0] + "?" + new Date().getTime();
                    }
                    window.location.reload();
                } else {
                    alert(data.message || "Upload failed.");
                }
            })
            .catch(() => {
                alert("Upload failed");
            });
        });
    }

});