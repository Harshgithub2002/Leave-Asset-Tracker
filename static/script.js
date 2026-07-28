document.addEventListener("DOMContentLoaded", function () {

    const forms = document.querySelectorAll("form");

    forms.forEach(form => {
        form.addEventListener("submit", function (e) {

            const username = form.querySelector("input[name='username']");
            const password = form.querySelector("input[name='password']");

            if (username && password) {

                if (username.value.trim().length < 3) {
                    alert("Username must be at least 3 characters long");
                    e.preventDefault();
                    return;
                }

                if (password.value.trim().length < 4) {
                    alert("Password must be at least 4 characters long");
                    e.preventDefault();
                    return;
                }
            }
        });
    });

});


// ------------------ Simple Logout Confirmation ------------------

function confirmLogout() {
    return confirm("Are you sure you want to logout?");
}
function showForm(type) {
    document.getElementById("requestForm").style.display = "block";
    document.getElementById("request_type").value = type;

    if (type === "wfh") {
        document.getElementById("leaveTypeDiv").style.display = "none";
    } else {
        document.getElementById("leaveTypeDiv").style.display = "block";
    }
}

function searchUser() {
    let input = document.getElementById("searchInput").value.toLowerCase();
    let list = document.getElementById("requestList").getElementsByTagName("li");

    for (let i = 0; i < list.length; i++) {
        let text = list[i].innerText.toLowerCase();
        list[i].style.display = text.includes(input) ? "" : "none";
    }
}
function toggleLeaveType() {
    let requestType = document.getElementById("request_type").value;
    let leaveType = document.getElementById("leave_type");

    if (requestType === "WFH") {
        leaveType.disabled = true;
        leaveType.value = "";
    } else {
        leaveType.disabled = false;
    }
}