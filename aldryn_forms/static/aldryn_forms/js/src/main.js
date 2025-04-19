import {
    enableFieldUploadDragAndDrop,
    disableButtonSubmit,
    handleRequiredFields,
    handleFormRequiredCheckbox,
    enableSubmitFromByFetch,
    sendData,
    toggleSubmitButton
} from './form'


document.addEventListener('DOMContentLoaded', () => {
    enableFieldUploadDragAndDrop()
    enableSubmitFromByFetch()

    // Disable button submit to prevent user click more than once.
    // Do not submit the form if any required fields are missing.
    for (const form of document.getElementsByTagName("form")) {
        if (!form.classList.contains("skip-disable-submit")) {
            form.addEventListener('submit', (event) => disableButtonSubmit(event, false))
        }
        if (!form.getAttribute("novalidate-checkbox-groups")) {
            // Enable submit button if required were set.
            form.addEventListener('submit', handleRequiredFields)
            for (const element of form.querySelectorAll(".form-required input[type=checkbox]")) {
                element.addEventListener('click', handleFormRequiredCheckbox)
            }
        }
        // Note: Must be the last in a series of checks!
        if (form.classList.contains("toggle-submit")) {
            toggleSubmitButton(form)
        }
    }
})

// Allow access from the entire document.
document.AldrynFormsSendData = sendData
