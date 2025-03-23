const toggleVisibility = (node) => {
    for (const item of node.getElementsByClassName("more")) {
        item.classList.toggle("d-none")
        if (item.classList.contains("d-none")) {
            node.title = "Display more."
        } else {
            node.title = "Display less."
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    for (const data of document.getElementsByClassName("aldryn-forms-data")) {
        data.style.cursor = "pointer"
        data.title = "Display less."
        data.addEventListener("click", (event) => {
            toggleVisibility(event.target.closest(".aldryn-forms-data"))
        })
    }

    const column = document.querySelector("#result_list th.column-display_data div.text")
    if (column) {
        const node = document.createElement("span")
        const icon = document.createElement("img")
        icon.src = "/static/admin/img/icon-viewlink.svg"
        icon.title = "Toggle more/less."
        node.appendChild(icon)
        node.style.cursor = "pointer"
        node.classList.add("item-after")
        node.addEventListener("click", () => {
            for (const item of document.getElementsByClassName("aldryn-forms-data")) {
                toggleVisibility(item)
            }
        })
        column.appendChild(node)
    }
})
