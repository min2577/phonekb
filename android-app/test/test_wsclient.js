var path = require('path')
var url = require('url')

var tasks = []

function makeTask() {
  var callbacks = {}
  var task = {
    onOpen: function(cb) { callbacks.open = cb },
    onMessage: function(cb) { callbacks.message = cb },
    onError: function(cb) { callbacks.error = cb },
    onClose: function(cb) { callbacks.close = cb },
    send: function() {},
    close: function(options) {
      setTimeout(function() {
        if (callbacks.close) callbacks.close(options || {})
      }, 0)
    },
  }
  tasks.push(task)
  return task
}

global.uni = {
  connectSocket: makeTask,
  closeSocket: function() {},
}

function wait(ms) {
  return new Promise(function(resolve) { setTimeout(resolve, ms) })
}

(async function() {
  var clientPath = path.resolve(__dirname, '../utils/wsclient.js')
  var clientUrl = url.pathToFileURL(clientPath).href
  var WS = (await import(clientUrl)).default

  WS.connect({ host: '127.0.0.1', port: 9876, code: 'ABCDEF' })
  await wait(350)
  if (tasks.length !== 1) throw new Error('expected one initial socket')

  WS.close()
  await wait(2200)
  if (tasks.length !== 1) throw new Error('manual close unexpectedly reconnected')

  console.log('  PASS manual close does not reconnect')
})().catch(function(error) {
  console.error('[test] ERROR:', error)
  process.exit(1)
})
