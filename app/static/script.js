// Пример JavaScript для валидации форм
function validateForm() {
    var email = document.forms["form"]["email"].value;
    var password = document.forms["form"]["password"].value;
    if (email == "" || password == "") {
        alert("Все поля должны быть заполнены");
        return false;
    }
}