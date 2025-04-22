/* global gettext */

// Prevent a situation when the translation is not implemented.
if (typeof gettext !== "function") {

    const django = {}

    django.catalog = {}

    window.gettext = function(msgid) {
        const value = django.catalog[msgid]
        if (typeof value === 'undefined') {
          return msgid
        } else {
          return (typeof value === 'string') ? value : value[0]
        }
    }
    window.ngettext = function(singular, plural, count) {
        const value = django.catalog[singular]
        if (typeof value === 'undefined') {
          return (count == 1) ? singular : plural
        } else {
          return value.constructor === Array ? value[django.pluralidx(count)] : value
        }
      }
    window.interpolate = function(fmt, obj, named) {
        if (named) {
          return fmt.replace(/%\(\w+\)s/g, function(match){return String(obj[match.slice(2,-2)])})
        } else {
          return fmt.replace(/%s/g, function(match){return String(obj.shift())})
        }
    }
}


export function toggleSubmitButton(form) {
    const requiredInputs = form.querySelectorAll('input[required], select[required], textarea[required], input[type=file]')

    const validateFieldset = () => {
        const allValid = Array.from(requiredInputs).every(input => input.checkValidity())
        if (form.dataset.toggle_submit) {
            form.dataset.toggle_submit(allValid)
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

    // Disable submit buttons.
    if (form.dataset.toggle_submit) {
        form.dataset.toggle_submit(false)
    } else {
        for(const submit of form.querySelectorAll('[type="submit"]')) {
            submit.disabled = true
        }
    }
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
                + interpolate(
                    ngettext(
                        "You have to choose at least %(value)s option (chosen %(chosen)s).",
                        "You have to choose at least %(value)s options (chosen %(chosen)s)."
                    ), {
                        value: checkboxset.dataset.required_min,
                        chosen: chosen
                    }, true)
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

    const listFileNames = getAttachmentsList(nodeInputFile)
    const form = nodeInputFile.closest("form")
    const asyncFetch = form.classList.contains("submit-by-fetch")

    let attachments = 0
    let total_size = 0

    if (asyncFetch && nodeInputFile.multiple) {
        for(const item of listFileNames.querySelectorAll("li")) {
            attachments += 1
            total_size += item.file.size
        }
    } else {
        listFileNames.innerHTML = ""
    }

    const accept = nodeInputFile.accept.length ? nodeInputFile.accept.split(',') : []
    const extensions = [],
        mimetypes = [],
        maim_mimes = [];

    const appendError = (listItem, message, name, text) => {
        const msg = document.createElement("div")
        msg.classList.add(name)
        msg.appendChild(document.createTextNode(text))
        message.appendChild(msg)
        listItem.classList.add("error")
        listItem.classList.add(name)
        nodeInputFile.setCustomValidity(text)
    }

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

    for (let i = 0; i < nodeInputFile.files.length; i++) {
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
        name.title = gettext("File size") + " " + humanFileSize(nodeInputFile.files[i].size)
        name.appendChild(document.createTextNode(file_name))
        content.appendChild(name)

        if (asyncFetch) {
            const remove = document.createElement("div")
            remove.classList.add("remove")
            const trash = document.createElement("img")
            trash.src = form.dataset.icon_trash ? form.dataset.icon_trash : "/static/aldryn_forms/img/trash.svg"
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
            icon.src = form.dataset.icon_attach ? form.dataset.icon_attach : "/static/aldryn_forms/img/attach-file.svg"
        } else {
            icon.src = form.dataset.icon_error ? form.dataset.icon_error : "/static/aldryn_forms/img/exclamation-mark.svg"
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

    const listFileNames = getAttachmentsList(nodeInputFile)

    // Recalculate all items for limit and size.
    let total_size = 0
    let attachments = 0
    for (const nodeLi of listFileNames.querySelectorAll("li")) {
        if (nodeLi.classList.contains("files-limit") && nodeInputFile.dataset.max_files !== null && attachments < nodeInputFile.dataset.max_files) {
            removeError(nodeLi, "files-limit")
        } else {
            attachments += 1
        }
        total_size += nodeLi.file.size
        if (nodeLi.classList.contains("file-size") && nodeInputFile.dataset.max_size !== null && total_size < nodeInputFile.dataset.max_size) {
            total_size -= nodeLi.file.size
            removeError(nodeLi, "file-size")
        }
    }
    if (!listFileNames.querySelectorAll("li.error").length) {
        nodeInputFile.setCustomValidity("")
        nodeInputFile.value = null
        // Trigger event Change to validate form.
        nodeInputFile.dispatchEvent(new Event("change"))
    }
}


function removeError(nodeLi, name) {
    for (const node of nodeLi.querySelectorAll(".content > .error > div." + name)) {
        node.remove()
    }
    nodeLi.classList.remove(name)
    if (!nodeLi.querySelectorAll(".content > .error > div").length) {
        nodeLi.classList.remove("error")
        for (const node of nodeLi.querySelectorAll(".status img")) {
            node.src = "/static/aldryn_forms/img/attach-file.svg"
        }
    }
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

    const form = input.closest("form")

    if (input.classList.contains("drag-and-drop")) {
        const label = document.createElement("div")
        label.classList.add("label")

        const icon = document.createElement("img")
        icon.src = form.dataset.icon_upload ? form.dataset.icon_upload : "/static/aldryn_forms/img/upload-one.svg"
        label.appendChild(icon)

        if (input.placeholder) {
            const title = document.createElement("h4")
            title.appendChild(document.createTextNode(input.placeholder))
            label.appendChild(title)
        }
        let labelText
        if (input.dataset.max_size && input.dataset.max_files) {
            labelText = interpolate(ngettext(
                "Max. %s file with a total size of max. %s",
                "Max. %s files with a total size of max. %s"
            ), [input.dataset.max_files, humanFileSize(input.dataset.max_size)])
        } else if (input.dataset.max_size) {
            labelText = gettext("Max. size") + " " + humanFileSize(input.dataset.max_size)
        }
        if (labelText) {
            const description = document.createElement("div")
            description.appendChild(document.createTextNode(labelText))
            label.appendChild(description)
        }
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
