const path = require('path')

module.exports = {
    mode: 'production',
    entry: {
        main: path.resolve(__dirname, 'aldryn_forms/static/aldryn_forms/js/src/main.js'),
        admin_list: path.resolve(__dirname, 'aldryn_forms/static/aldryn_forms/js/src/admin-list.js')
    },
    output: {
        filename: '[name].js',
        path: path.resolve(__dirname, 'aldryn_forms/static/aldryn_forms/js/'),
    },
    devtool: 'source-map',
    devServer: {
        contentBase: path.resolve(__dirname, 'aldryn_forms/static/aldryn_forms/js/'),
    },
}
