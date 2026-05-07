// Runs after the page fully loads.
document.addEventListener("DOMContentLoaded", function () {

    // Gets the profile display section, edit form, and buttons.
    const displayMode = document.getElementById("displayMode");
    const editForm = document.getElementById("editForm");
    const editBtn = document.getElementById("editBtn");
    const cancelBtn = document.getElementById("cancelBtn");

    // Gets the avatar elements used for uploading and displaying the profile picture.
    const avatarWrapper = document.getElementById("avatarWrapper");
    const avatarInput = document.getElementById("avatarInput");
    const avatarImg = document.getElementById("userAvatar");

    // Saves the original form values so changes can be detected later.
    let originalFormData = new FormData(editForm);

    // -------------------
    // ENTER EDIT MODE
    // -------------------
    if (editBtn) {

        editBtn.addEventListener("click", function () {

            // Hides the display view and shows the editable form.
            displayMode.style.display = "none";
            editForm.style.display = "block";

            // Saves the current form state when edit mode starts.
            originalFormData = new FormData(editForm);
        });
    }

    // -------------------
    // CANCEL EDIT MODE
    // -------------------
    if (cancelBtn) {

        cancelBtn.addEventListener("click", function () {

            const currentFormData = new FormData(editForm);

            let hasChanges = false;

            // Compares the current form values to the original values.
            for (let [key, value] of currentFormData.entries()) {

                if (originalFormData.get(key) !== value) {
                    hasChanges = true;
                    break;
                }
            }

            // Warns the user before discarding unsaved changes.
            if (hasChanges) {

                const confirmLeave = confirm("Are you sure you want to discard your changes?");

                if (!confirmLeave) return;
            }

            // Switches back to display mode and resets the form.
            displayMode.style.display = "block";
            editForm.style.display = "none";
            editForm.reset();
        });
    }

    // -------------------
    // AVATAR CLICK
    // -------------------
    if (avatarWrapper) {

        avatarWrapper.addEventListener("click", function () {

            // Opens the hidden file input when the avatar is clicked.
            avatarInput.click();
        });
    }

    // -------------------
    // AVATAR UPLOAD
    // -------------------
    if (avatarInput) {

        avatarInput.addEventListener("change", function (e) {

            const file = e.target.files[0];

            if (!file) return;

            // Only allows common image file types.
            const allowedTypes = ["image/png", "image/jpeg", "image/jpg", "image/gif"];

            if (!allowedTypes.includes(file.type)) {
                alert("Only PNG, JPEG, and GIF images are allowed.");
                return;
            }

            // Limits profile pictures to 2MB.
            if (file.size > 2 * 1024 * 1024) {
                alert("Image must be under 2MB.");
                return;
            }

            // Creates form data for the avatar upload request.
            const formData = new FormData();

            formData.append("avatar", file);

            // Sends the avatar file to the profile route without a full form submit.
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

                    // Refreshes the avatar image by adding a timestamp to the URL.
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