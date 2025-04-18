/* global gettext */

// Prevent a situation when the translation is not implemented.
if (typeof gettext !== "function") {
    window.gettext = text => text
}

export function validateForm(form) {
    const requiredInputs = form.querySelectorAll('input[required], select[required], textarea[required], input[type=file]')

    const validateFieldset = () => {
        // console.log("requiredInputs:", requiredInputs)
        const allValid = Array.from(requiredInputs).every(input => input.checkValidity())
        // console.log("validateFieldset() allValid:", allValid)
        if (form.dataset.validate_result) {
            form.dataset.validate_result(allValid)
        } else {
            for(const submit of form.querySelectorAll('[type="submit"]')) {
                submit.disabled = !allValid
            }
        }
    }
    // Add event listeners to all required inputs
    requiredInputs.forEach(input => {
        input.addEventListener('input', validateFieldset)   // for text inputs
        input.addEventListener('change', validateFieldset)  // for checkboxes, selects, etc.
    })

    // // DEBUG:
    // for(const node of form.querySelectorAll('input[type=file]')) {
    //     node.addEventListener('change', (event) => {
    //         console.log("Dispatch event CHANGE", event)
    //         console.log("this.files:", event.target.files)
    //         // console.log("validateFieldset")
    //         // validateFieldset()
    //     })
    //     node.addEventListener('drop', (event) => {
    //         console.log("Dispatch event DROP", event)
    //         console.log("this.files:", event.target.files)
    //     })
    // }

    // Disable submit buttons.
    for(const submit of form.querySelectorAll('[type="submit"]')) {
        submit.disabled = true
    }
}


function populate(text, obj) {
    // Map values to the text. E.g. "Text %(value)s."
    for (const [key, value] of Object.entries(obj)) {
        const pattern = new RegExp(`%\\(${key}\\)s`, 'g')
        text = text.replace(pattern, value)
    }
    return text
}


export function handleFormRequiredCheckbox(event) {
    // The event.target is a checkbox - this is the result of selector: .form-required input[type=checkbox]
    const form = event.target.closest("form")
    if (form) {
        // Remove error messages if there are any.
        for (const element of form.querySelectorAll(".aldryn-forms-required-msg, .aldryn-forms-submit-msg")) {
            element.parentNode.removeChild(element)
        }
        // Enable submit button.
        for (const button of form.querySelectorAll('[type=submit]')) {
            button.disabled = false
            button.readOnly = false
        }
    }
}

export function disableButtonSubmit(event, display_message) {
    // Disable button submit to prevent user click more than once.
    event.target.blur()
    for (const button of event.target.querySelectorAll('[type=submit]')) {
        button.disabled = true
        button.readOnly = true
        if (display_message) {
            const form = event.target.closest("form")
            const message = form && form.dataset.message_wait ? form.dataset.message_wait : gettext("Please wait. Submitting form...")
            button.insertAdjacentHTML(
                'afterend',
                '<div class="text-danger aldryn-forms aldryn-forms-submit-msg">' + message + '</div>')
        }
    }
}


function enableButtonSubmit(form) {
    for (const button of form.querySelectorAll('[type=submit]')) {
        button.disabled = false
        button.readOnly = false
    }
    for (const msg of form.querySelectorAll('.aldryn-forms-submit-msg')) {
        msg.remove()
    }
}


export function handleRequiredFields(event) {
    // Handle required fields.
    let requiredFieldsFulfilled = true
    for (const checkboxset of this.getElementsByClassName("form-required")) {
        const chosen = checkboxset.querySelectorAll("input[type=checkbox]:checked").length
        if (chosen < parseInt(checkboxset.dataset.required_min)) {
            requiredFieldsFulfilled = false
            checkboxset.insertAdjacentHTML(
                'afterend',
                '<div class="text-danger aldryn-forms aldryn-forms-required-msg">'
                + populate(gettext("You have to choose at least %(value)s options (chosen %(chosen)s)."), {
                    value: checkboxset.dataset.required_min, chosen: chosen})
                + '</div>')
        }
    }
    // Do not submit the form if any required fields are missing.
    if (requiredFieldsFulfilled) {
        // Display a message to inform the user that the form has been submitted.
        for (const button of this.querySelectorAll('[type=submit]')) {
            button.insertAdjacentHTML(
                'afterend',
                '<div class="text-danger aldryn-forms aldryn-forms-submit-msg">'
                + gettext("Please wait. Submitting form...")
                + '</div>')
        }
    } else {
        // Some required value is not set.
        event.preventDefault()
        for (const button of this.querySelectorAll('[type=submit]')) {
            button.insertAdjacentHTML(
                'afterend', '<div class="text-danger aldryn-forms aldryn-forms-submit-msg">'
                + gettext("Correct the errors first, please.") + '</div>')
        }
    }
}

/*
function blockSubmit(nodeInput) {
    const form = nodeInput.closest("form")
    for (const button of form.querySelectorAll('[type=submit]')) {
        button.disabled = true
        button.insertAdjacentHTML(
            'afterend', '<div class="text-danger aldryn-forms aldryn-forms-submit-msg">'
            + gettext("Correct the errors first, please.") + '</div>')
    }
}


function unblockSubmit(nodeInput) {
    const form = nodeInput.closest("form")
    for (const button of form.querySelectorAll('[type=submit]')) {
        button.disabled = false
    }
    for (const element of form.getElementsByClassName('aldryn-forms-submit-msg')) {
        element.remove()
    }
}
*/

function displayNodeMessages(node, messages, class_name) {
    node.insertAdjacentHTML(
        'afterend',
        `<ul class="messages aldryn-forms-post-message"><li class="${class_name}">`
        + messages.join(`</li><li class="${class_name}">`) + '</ul>') + '</ul>'
}

function displayMessage(form, message, class_name) {
    for (const button of form.querySelectorAll('[type=submit]')) {
        button.insertAdjacentHTML(
            'afterend',
            `<ul class="messages aldryn-forms-post-message">
                <li class="${class_name}">${message}</li>
            </ul>`)
    }
}

function removeMessages(form) {
    for (const node of form.querySelectorAll('.aldryn-forms-post-message')) {
        node.remove()
    }
}

function humanFileSize(size) {
    var i = size == 0 ? 0 : Math.floor(Math.log(size) / Math.log(1024));
    return +((size / Math.pow(1024, i)).toFixed(2)) * 1 + ' ' + ['B', 'kB', 'MB', 'GB', 'TB'][i];
}

function getAttachmentsList(nodeInputFile) {
    const frame = nodeInputFile.closest("." + uploadFilesFrame)
    return frame.querySelector("ul.upload-file-names")
}

function handleChangeFilesList(nodeInputFile) {
    // unblockSubmit(nodeInputFile)

    const listFileNames = getAttachmentsList(nodeInputFile)
    const form = nodeInputFile.closest("form")
    const asyncFetch = form.classList.contains("submit-by-fetch")
    // console.log("listFileNames:", listFileNames)
    // console.log("asyncFetch:", asyncFetch)

    let attachments = 0
    let total_size = 0

    if (asyncFetch) {
        // attachments = listFileNames.querySelectorAll("li").length
        for(const item of listFileNames.querySelectorAll("li")) {
            attachments += 1
            total_size += item.file.size
        }
    } else {
        // attachments = 0
        // total_size = 0
        listFileNames.innerHTML = ""
    }
    // console.log("attachments:", attachments)
    // console.log("total_size:", total_size)

    const accept = nodeInputFile.accept.length ? nodeInputFile.accept.split(',') : []
    const extensions = [],
        mimetypes = [],
        maim_mimes = [];

    // let total_size = 0;

    const appendError = (listItem, message, name, text) => {
        // errors.push(text)
        const msg = document.createElement("div")
        msg.classList.add(name)
        msg.appendChild(document.createTextNode(text))
        message.appendChild(msg)
        listItem.classList.add("error")
        listItem.classList.add(name)
        // nodeInputFile.classList.add("error")
        nodeInputFile.setCustomValidity(text)
        // console.log("nodeInputFile.setCustomValidity", text)
    }

    // let is_valid = true
    /*
    let files_size_summary = null
    if (nodeInputFile.dataset.max_size !== null) {
        files_size_summary = 0
        for (let i = 0; i < nodeInputFile.files.length; i++) {
            files_size_summary += nodeInputFile.files[i].size
        }
    }
    if (nodeInputFile.dataset.max_size !== null && files_size_summary > nodeInputFile.dataset.max_size) {
        is_valid = false
        const msg = document.createElement("li")
        msg.classList.add("text-danger")
        msg.appendChild(document.createTextNode(gettext('The total file size has exceeded the specified limit.')))
        listFileNames.appendChild(msg)
    }
    */

    if (nodeInputFile.accept.length) {
        for (let i = 0; i < accept.length; i++) {
            if (accept[i][0] === '.') {
                extensions.push(accept[i])
            } else {
                const mtypes = accept[i].split('/')
                if (mtypes[1] === '*') {
                    maim_mimes.push(mtypes[0])
                } else {
                    mimetypes.push(accept[i])
                }
            }
        }
    }

    console.log("extensions:", extensions)
    console.log("mimetypes:", mimetypes)

    let number_items_exceeded = false

    // console.log("nodeInputFile.files.length:", nodeInputFile.files.length)

    for (let i = 0; i < nodeInputFile.files.length; i++) {
        // console.log("file type:", nodeInputFile.files[i].type)
        attachments += 1

        const listItem = document.createElement("li")
        listItem.file = nodeInputFile.files[i]

        const file_name = nodeInputFile.files[i].name

        const status = document.createElement("div")
        status.classList.add("status")
        listItem.appendChild(status)

        const content = document.createElement("div")
        content.classList.add("content")
        listItem.appendChild(content)

        const name = document.createElement("div")
        name.classList.add("file-name")
        name.title = humanFileSize(nodeInputFile.files[i].size)
        name.appendChild(document.createTextNode(file_name))
        // name.appendChild(document.createTextNode(" " + humanFileSize(nodeInputFile.files[i].size)))
        content.appendChild(name)

        if (asyncFetch) {
            const remove = document.createElement("div")
            remove.classList.add("remove")
            const trash = document.createElement("img")
            trash.src = "/static/aldryn_forms/img/trash.svg"
            trash.classList.add("trash")
            trash.style.cursor = "pointer"
            trash.alt = trash.title = gettext("Remove file.")
            remove.appendChild(trash)
            listItem.appendChild(remove)
            trash.addEventListener("click", removeAttachment)
        }

        const message = document.createElement("div")
        message.classList.add("error")
        content.appendChild(message)

        let valid = true
        if (nodeInputFile.dataset.max_files !== null && attachments > nodeInputFile.dataset.max_files) {
            valid = false
            appendError(listItem, message, "files-limit", gettext('This file exceeds the uploaded files limit.'))
            number_items_exceeded = true
        }

        let is_expected_type = accept.length ? false : true

        if (!is_expected_type && extensions) {
            const ext = file_name.toLowerCase().match(/\.\w+$/)
            if (ext !== null && extensions.includes(ext[0])) {
                is_expected_type = true
            }
        }
        if (!is_expected_type && mimetypes) {
            if (mimetypes.includes(nodeInputFile.files[i].type)) {
                is_expected_type = true
            }
        }
        if (!is_expected_type && maim_mimes) {
            const mt = nodeInputFile.files[i].type.split('/')
            if (maim_mimes.includes(mt[0])) {
                is_expected_type = true
            }
        }

        if (!is_expected_type) {
            valid = false
            appendError(listItem, message, "file-type", gettext('The file type is not among the accpeted types.'))
        }

        total_size += nodeInputFile.files[i].size
        if (nodeInputFile.dataset.max_size !== null && total_size > nodeInputFile.dataset.max_size) {
            valid = false
            appendError(listItem, message, "file-size", gettext('The total size of all files has exceeded the specified limit.'))
        }

        const icon = document.createElement("img")
        if (valid) {
            icon.src = "/static/aldryn_forms/img/attach-file.svg"
        } else {
            icon.src = "/static/aldryn_forms/img/exclamation-mark.svg"
        }
        status.appendChild(icon)

        listFileNames.appendChild(listItem)

        if (number_items_exceeded) {
            break
        }
    }
}

function removeAttachment(event) {
    let nodeInputFile
    try {
        const listFileNames = event.target.closest("ul")
        const frame = listFileNames.closest("." + uploadFilesFrame)
        nodeInputFile = frame.querySelector("input[type=file]")
    } catch (error) {
        console.error(error)
        return
    }
    event.target.closest("li").remove()

    // const listFileNames = event.target.closest("ul")
    const listFileNames = getAttachmentsList(nodeInputFile)
    console.log("listFileNames:", listFileNames)

    // TODO: recalculate all items for limit and size.
    // if (!listFileNames.querySelectorAll("li.error").length) {
    //     const frame = listFileNames.closest("." + uploadFilesFrame)
    //     const nodeInputFile = frame.querySelector("input[type=file]")
    //     nodeInputFile.setCustomValidity("")
    //     // Trigger event Change to validate form.
    //     nodeInputFile.value = null
    //     nodeInputFile.dispatchEvent(new Event("change"))
    // }

    // Recalculate all items for limit and size.
    let total_size = 0
    let attachments = 0
    for (const nodeLi of listFileNames.querySelectorAll("li")) {
        // console.log("nodeLi:", nodeLi, "attachments:", attachments, "total_size:", total_size)
        // console.log("? limit:", nodeLi.classList.contains("files-limit"))
        // console.log("? nodeInputFile.dataset.max_files:", nodeInputFile.dataset.max_files, "attachments:", attachments)
        if (nodeLi.classList.contains("files-limit") && nodeInputFile.dataset.max_files !== null && attachments < nodeInputFile.dataset.max_files) {
            // TODO: remove message, remove parent, if is empty.
            console.log("!!! removeError", nodeLi)
            removeError(nodeLi, "files-limit")
            // for (const node of nodeLi.querySelectorAll(".files-limit")) {
            //     node.remove()
            // }
            // nodeLi.classList.remove("files-limit")
            // if (!nodeLi.querySelectorAll(".error div").length) {
            //     for (const node of nodeLi.querySelectorAll(".error")) {
            //         node.remove()
            //     }
            //     nodeLi.classList.remove("error")
            // }
        } else {
            attachments += 1
        }
        console.log("??? file-size:", nodeLi.classList.contains("file-size"))
        console.log("??? nodeInputFile.dataset.max_size:", nodeInputFile.dataset.max_size, "total_size:", total_size)
        total_size += nodeLi.file.size
        if (nodeLi.classList.contains("file-size") && nodeInputFile.dataset.max_size !== null && total_size < nodeInputFile.dataset.max_size) {
            // TODO: remove message, remove parent, if is empty.
            total_size -= nodeLi.file.size
            console.log("!!! REMOVE file-size !!!", nodeLi)
            removeError(nodeLi, "file-size")
        }
        // TODO: remove class error from li, if it does not have errors.
    }
    if (!listFileNames.querySelectorAll("li.error").length) {
        // Trigger event Change to validate form.
        nodeInputFile.setCustomValidity("")
        nodeInputFile.value = null
        nodeInputFile.dispatchEvent(new Event("change"))
    }
}


function removeError(nodeLi, name) {
    document.xxx = nodeLi
    console.log("----------------------------")
    console.log("removeError", nodeLi, name)
    for (const node of nodeLi.querySelectorAll(".content > .error > div." + name)) {
        console.log("1.node.remove():", node)
        node.remove()
    }
    nodeLi.classList.remove(name)
    console.log("??? .content > .error > div:", nodeLi.querySelectorAll(".content > .error > div").length)
    document.xxx.querySelectorAll(".content > .error")
    if (!nodeLi.querySelectorAll(".content > .error > div").length) {
        // for (const node of nodeLi.querySelectorAll(".error")) {
        //     console.log("2.node.remove():", node)
        //     node.remove()
        // }
        nodeLi.classList.remove("error")
        for (const node of nodeLi.querySelectorAll(".status img")) {
            node.src = "/static/aldryn_forms/img/attach-file.svg"
        }
    }
// document.xxx.classList.remove("error")
}


const uploadFilesFrame = "upload-files-frame"


function dragAndDropFields(input) {
    input.classList.add("check-validity")
    const uploadFileFrame = document.createElement("div")
    uploadFileFrame.classList.add(uploadFilesFrame)
    if (input.classList.contains("drag-and-drop")) {
        uploadFileFrame.classList.add("drag-and-drop")
    }
    const dragAndDrop = document.createElement("div")
    dragAndDrop.classList.add("drag-and-drop")
    uploadFileFrame.appendChild(dragAndDrop)

    if (input.classList.contains("drag-and-drop")) {
        const label = document.createElement("div")
        label.classList.add("label")

        const icon = document.createElement("img")
        icon.src = "/static/aldryn_forms/img/upload-one.svg"
        label.appendChild(icon)

        if (input.placeholder) {
            const title = document.createElement("h4")
            title.appendChild(document.createTextNode(input.placeholder))
            label.appendChild(title)
        }
        if (input.dataset.max_size) {
            const description = document.createElement("div")
            description.appendChild(document.createTextNode(gettext("Max. size") + " " + humanFileSize(input.dataset.max_size)))
            label.appendChild(description)
        }
        // TODO:
        // Celkem max. velikost 5 MB
        // Max 3 souborů o celkem max. velikosti 5 MB
        dragAndDrop.appendChild(label)
    }

    let helpText
    if (input.nextElementSibling.classList.contains("help-text")) {
        helpText = input.nextElementSibling
        helpText.parentElement.removeChild(helpText)
    }

    input.parentNode.insertBefore(uploadFileFrame, input)
    input.parentElement.removeChild(input)
    dragAndDrop.appendChild(input)

    if (helpText) {
        uploadFileFrame.appendChild(helpText)
    }

    // <ul class="upload-file-names"></ul>
    const listFileNames = document.createElement("ul")
    listFileNames.classList.add("upload-file-names")
    uploadFileFrame.appendChild(listFileNames)

    const form = input.closest("form")
    form.classList.add("adjust-uploads")
    input.addEventListener('change', (event) => handleChangeFilesList(event.target), false)
}


export function enableFieldUploadDragAndDrop() {
    for (const input of document.querySelectorAll('input[type=file]')) {
        if (input.dataset.enable_js !== undefined) {
            dragAndDropFields(input)
        }
    }
}

function adjustUploads(form) {
    const formData = new FormData(form)
    const attachment_names = []
    for (const pair of formData.entries()) {
        if (pair[1] instanceof File && !attachment_names.includes(pair[0])) {
            attachment_names.push(pair[0])
        }
    }
    for(const name of attachment_names) {
        formData.delete(name)
    }
    for(const name of attachment_names) {
        const input = form.querySelector(`input[name=${name}]`)
        if (!input) {
            continue
        }
        const frame = input.closest("." + uploadFilesFrame)
        if (!frame) {
            continue
        }
        for(const attachment of frame.querySelectorAll(".upload-file-names li")) {
            formData.append(name, attachment.file)
        }
    }
    return formData
}


export async function sendData(form) {
    removeMessages(form)
    const formData = form.classList.contains("adjust-uploads") ? adjustUploads(form) : new FormData(form)
    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: formData,
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
        const data = await response.json()
        console.log(data)
        if (data.status === "ERROR") {
            for (const name in data.form) {
                if (name === "__all__") {
                    const button = form.querySelector('[type=submit]')
                    if (button) {
                        displayNodeMessages(button, data.form[name], "error")
                    } else {
                        displayMessage(form, data.form[name], "error")
                    }
                } else {
                    const input = form.querySelector(`input[name="${name}"]`)
                    if (input) {
                        displayNodeMessages(input, data.form[name], "error")
                    }
                }
            }
        } else {
            if (form.dataset.run_next) {
                document[form.dataset.run_next](form, data)
            } else {
                displayMessage(form, data.message, "success")
            }
        }
    } catch (e) {
        displayMessage(form, e, "error")
    } finally {
        enableButtonSubmit(form)
    }
}


export function enableSubmitFromByFetch() {
    for (const form of document.querySelectorAll('form.submit-by-fetch')) {
        form.addEventListener("submit", (event) => {
            event.preventDefault()
            sendData(form)
        })
    }
}
