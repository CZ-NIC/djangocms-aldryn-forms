// For usage, see help in template aldryn_forms/templates/admin/aldryn_forms/formplugin/change_form.html

function parseConfig(value) {
    if (!value) {
        return null
    }
    try {
        return JSON.parse(value)
    } catch (e) {
        console.error('Invalid format:', e)
        return null
    }
}

const performActions = (field, actions) => {
    for (const action of actions) {
        if (typeof action === 'string') {
            if (action === 'enable') {
                field.disabled = false
            } else if (action === 'disable') {
                field.disabled = true
            } else if (action === 'required') {
                field.required = true
            } else if (action === 'optional') {
                field.required = false
            }
        } else if (action !== null && typeof action === 'object') {
            Object.entries(action).forEach(([command, value]) => {
                if (command === 'set') {
                    if (field.type === 'checkbox' || field.type === 'radio') {
                        field.checked = value
                    } else {
                        field.value = value
                    }
                }
            })
        }
    }
}

const processCommandForFields = (form, process) => {
    for (const statement of process) {
        Object.entries(statement).forEach(([field_name, actions]) => {
            for (const field of form.querySelectorAll(getSelector(field_name))) {
                performActions(field, actions)
            }
        })
    }
}

const addEvent = (form, field, event_name, fields) => {
    field.addEventListener(event_name, (e) => {
        Object.entries(fields).forEach(([field_value, process]) => {
            if (e.target.value === field_value) {
                processCommandForFields(form, process)
            }
        })
    })
}

const camelCase = (text) => {
    return text.replace(/-(\w)/g, (_, char) => char.toUpperCase())
}

const getSelector = (name) => {
    const match = name.match(/(\w+)\[(\w+)\]/)
    const selector = match ? `[name=${match[1]}][value=${match[2]}]` : `[name=${name}]`
    return selector
}

const processConfig = (selector, fnc) => {
    for (const form of document.querySelectorAll(`[data-${selector}]`)) {
        const result = parseConfig(form.dataset[camelCase(selector)])
        if (!result) {
            continue
        }
        Object.entries(result).forEach(([name, params]) => {
            for (const field of form.querySelectorAll(getSelector(name))) {
                fnc(form, field, params)
            }
        })
    }
}

const addEventForFields = (form, field, params) => {
    Object.entries(params).forEach(([command, fields]) => {
        addEvent(form, field, command, fields)
    })
}

export const initFormFields = () => processConfig('init-field-state', (form, field, params) => performActions(field, params))
export const addEventsToFormFields = () => processConfig('add-field-events', addEventForFields)
