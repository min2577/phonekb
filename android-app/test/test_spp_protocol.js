var path = require('path')
var url = require('url')

;(async function() {
  var mod = await import(url.pathToFileURL(path.resolve(__dirname, '../utils/sppProtocol.js')).href)
  var failed = 0
  function assert(condition, message) {
    if (condition) console.log('  PASS', message)
    else { console.error('  FAIL', message); failed++ }
  }

  var text = JSON.stringify({ action: 'type', text: '中文输入🙂' })
  var packet = mod.encodePacket(text)
  var decoder = new mod.PacketDecoder()
  var out = []
  for (var i = 0; i < packet.length; i++) out = out.concat(decoder.feed(packet.slice(i, i + 1)))
  assert(out.length === 1, 'fragmented packet decoded once')
  assert(mod.utf8Decode(out[0]) === text, 'UTF-8 Chinese and emoji round trip')

  var first = mod.encodePacket('{"action":"ping"}')
  var second = mod.encodePacket('{"action":"reload_layouts"}')
  var joined = new Uint8Array(first.length + second.length)
  joined.set(first); joined.set(second, first.length)
  out = new mod.PacketDecoder().feed(joined)
  assert(out.length === 2, 'coalesced packets decoded separately')

  var noisy = new Uint8Array(3 + first.length)
  noisy.set([1, 2, 3]); noisy.set(first, 3)
  out = new mod.PacketDecoder().feed(noisy)
  assert(out.length === 1 && mod.utf8Decode(out[0]).indexOf('ping') >= 0, 'parser recovers after noise')

  process.exit(failed ? 1 : 0)
})().catch(function(error) { console.error(error); process.exit(1) })
