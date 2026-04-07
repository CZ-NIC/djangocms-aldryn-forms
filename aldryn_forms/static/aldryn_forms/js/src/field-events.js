// For usage, see help in template aldryn_forms/templates/admin/aldryn_forms/formplugin/change_form.html

let debug = false


const parseConfig = (value) => {
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

const performActions = (form, field, actions) => {
    if (debug) {
        console.log(`Perform actions for field "${field.tagName}" with name "${field.getAttribute('name')}".`)
    }
    for (const action of actions) {
        if (typeof action === 'string') {
            if (debug) {
                console.log(`Perform action "${action}"`)
            }
            if (action === 'enable') {
                field.disabled = false
            } else if (action === 'disable') {
                field.disabled = true
            } else if (action === 'required') {
                field.required = true
            } else if (action === 'optional') {
                field.required = false
            } else if (action === 'submit') {
                form.requestSubmit()
            } else {
                console.error(`Unknown action ${action}`)
            }
        } else if (action !== null && typeof action === 'object') {
            Object.entries(action).forEach(([command, value]) => {
                if (debug) {
                    console.log(`Perform command "${command}"`)
                }
                if (command === 'set') {
                    if (field.type === 'checkbox' || field.type === 'radio') {
                        field.checked = value
                    } else {
                        if (['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(field.tagName)) {
                            field.value = value
                        } else {
                            const className = 'field-value'
                            let node = field.querySelector(`.${className}`)
                            if  (!node) {
                                node = document.createElement('span')
                                node.classList.add(className)
                                field.appendChild(node)
                            }
                            node.textContent = value
                        }
                    }
                } else if (command === 'addclasses') {
                    if (typeof value === 'string') {
                        value = [value]
                    }
                    field.classList.add(...value)
                } else if (command === 'removeclasses') {
                    if (typeof value === 'string') {
                        value = [value]
                    }
                    field.classList.remove(...value)
                } else {
                    console.error(`Unknown command ${command}`)
                }
            })
        }
    }
}

const processCommandForFields = (form, process) => {
    for (const statement of process) {
        Object.entries(statement).forEach(([field_name, actions]) => {
            for (const field of form.querySelectorAll(getSelector(field_name))) {
                performActions(form, field, actions)
            }
        })
    }
}

const addEvent = (form, field, event_name, fields) => {
    if (debug) {
        console.log(`Set event "${event_name}" to field "${field.name}"`)
    }
    field.addEventListener(event_name, (e) => {
        Object.entries(fields).forEach(([field_value, process]) => {
            if (field.type === 'checkbox' && [true, false, 'true', 'false'].includes(field_value)) {
                const checked = typeof field_value === 'string' ? field_value === 'true' : field_value
                if (e.target.checked === checked) {
                    processCommandForFields(form, process)
                }
            } else {
                if (e.target.value === field_value) {
                    processCommandForFields(form, process)
                }
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
        const config = parseConfig(form.dataset[camelCase(selector)])
        if (!config) {
            continue
        }
        Object.entries(config).forEach(([name, params]) => {
            if (debug) {
                console.log(`Try to set field by name "${name}"`)
            }
            for (const field of form.querySelectorAll(getSelector(name))) {
                if (debug) {
                    console.log(`Set field "${name}"`)
                }
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

export const initDebugMode = () => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('debug') === 'true') {
        debug = true
        console.log('Set debug mode.')
    }
}

export const initFormFields = () => processConfig('init-field-state', performActions)
export const addEventsToFormFields = () => processConfig('add-field-events', addEventForFields)
