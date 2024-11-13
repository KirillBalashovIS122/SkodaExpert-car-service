function validateForm() {
    var fullName = document.getElementById("full_name").value;
    var carModel = document.getElementById("car_model").value;
    var carVin = document.getElementById("car_vin").value;
    var carPlate = document.getElementById("car_plate").value;
    var phone = document.getElementById("phone").value;
    var carYear = document.getElementById("car_year").value;
    var appointmentDate = document.getElementById("appointment_date").value;

    if (fullName === "" || carModel === "" || carVin === "" || carPlate === "" || phone === "" || carYear === "" || appointmentDate === "") {
        alert("Все поля должны быть заполнены");
        return false;
    }

    if (carVin.length !== 17) {
        alert("VIN-номер должен состоять из 17 символов");
        return false;
    }

    return true;
}

document.getElementById('appointmentForm').addEventListener('submit', function(event) {
    event.preventDefault();

    if (!validateForm()) {
        return;
    }

    var form = event.target;
    var formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = "{{ url_for('main.appointment_success') }}";
        } else {
            alert('Ошибка при записи на ремонт');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Произошла ошибка при отправке формы');
    });
});