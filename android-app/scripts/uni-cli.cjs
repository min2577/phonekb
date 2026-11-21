const path = require('path')

const projectDir = path.resolve(__dirname, '..')
process.env.UNI_INPUT_DIR = projectDir
process.env.UNI_OUTPUT_DIR = path.join(projectDir, 'unpackage', 'dist', 'build', 'app-plus')

require('@dcloudio/vite-plugin-uni/bin/uni.js')
