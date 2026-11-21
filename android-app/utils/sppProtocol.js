// PhoneKB SPP v2: "PKB2" + uint32 big-endian UTF-8 payload length + payload.
export const SPP_MAGIC = [0x50, 0x4B, 0x42, 0x32]
export const SPP_MAGIC_INT = 0x504B4232
export const SPP_MAX_PAYLOAD = 256 * 1024

export function utf8Encode(text) {
  const out = []
  const value = String(text || '')
  for (let i = 0; i < value.length; i++) {
    let code = value.charCodeAt(i)
    if (code >= 0xD800 && code <= 0xDBFF && i + 1 < value.length) {
      const low = value.charCodeAt(i + 1)
      if (low >= 0xDC00 && low <= 0xDFFF) {
        code = 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00)
        i++
      }
    }
    if (code <= 0x7F) out.push(code)
    else if (code <= 0x7FF) {
      out.push(0xC0 | (code >> 6), 0x80 | (code & 0x3F))
    } else if (code <= 0xFFFF) {
      out.push(0xE0 | (code >> 12), 0x80 | ((code >> 6) & 0x3F), 0x80 | (code & 0x3F))
    } else {
      out.push(0xF0 | (code >> 18), 0x80 | ((code >> 12) & 0x3F), 0x80 | ((code >> 6) & 0x3F), 0x80 | (code & 0x3F))
    }
  }
  return new Uint8Array(out)
}

export function utf8Decode(bytes) {
  let out = ''
  for (let i = 0; i < bytes.length;) {
    const first = bytes[i++] & 0xFF
    let code
    if (first < 0x80) code = first
    else if ((first & 0xE0) === 0xC0 && i < bytes.length) {
      code = ((first & 0x1F) << 6) | (bytes[i++] & 0x3F)
    } else if ((first & 0xF0) === 0xE0 && i + 1 < bytes.length) {
      code = ((first & 0x0F) << 12) | ((bytes[i++] & 0x3F) << 6) | (bytes[i++] & 0x3F)
    } else if ((first & 0xF8) === 0xF0 && i + 2 < bytes.length) {
      code = ((first & 0x07) << 18) | ((bytes[i++] & 0x3F) << 12) | ((bytes[i++] & 0x3F) << 6) | (bytes[i++] & 0x3F)
    } else {
      code = 0xFFFD
    }
    if (code <= 0xFFFF) out += String.fromCharCode(code)
    else {
      code -= 0x10000
      out += String.fromCharCode(0xD800 | (code >> 10), 0xDC00 | (code & 0x3FF))
    }
  }
  return out
}

export function encodePacket(payload) {
  const body = payload instanceof Uint8Array ? payload : utf8Encode(payload)
  if (body.length <= 0 || body.length > SPP_MAX_PAYLOAD) throw new Error('invalid SPP payload length: ' + body.length)
  const packet = new Uint8Array(8 + body.length)
  packet.set(SPP_MAGIC, 0)
  packet[4] = (body.length >>> 24) & 0xFF
  packet[5] = (body.length >>> 16) & 0xFF
  packet[6] = (body.length >>> 8) & 0xFF
  packet[7] = body.length & 0xFF
  packet.set(body, 8)
  return packet
}

export class PacketDecoder {
  constructor(maxPayload) {
    this.maxPayload = maxPayload || SPP_MAX_PAYLOAD
    this.buffer = new Uint8Array(0)
  }

  feed(chunk) {
    const incoming = chunk instanceof Uint8Array ? chunk : new Uint8Array(chunk || [])
    const joined = new Uint8Array(this.buffer.length + incoming.length)
    joined.set(this.buffer, 0)
    joined.set(incoming, this.buffer.length)
    this.buffer = joined
    const packets = []
    while (this.buffer.length >= 4) {
      let start = -1
      for (let i = 0; i <= this.buffer.length - 4; i++) {
        if (this.buffer[i] === 0x50 && this.buffer[i + 1] === 0x4B && this.buffer[i + 2] === 0x42 && this.buffer[i + 3] === 0x32) { start = i; break }
      }
      if (start < 0) { this.buffer = this.buffer.slice(Math.max(0, this.buffer.length - 3)); break }
      if (start > 0) this.buffer = this.buffer.slice(start)
      if (this.buffer.length < 8) break
      const size = ((this.buffer[4] * 0x1000000) + (this.buffer[5] << 16) + (this.buffer[6] << 8) + this.buffer[7]) >>> 0
      if (size <= 0 || size > this.maxPayload) { this.buffer = this.buffer.slice(1); continue }
      if (this.buffer.length < 8 + size) break
      packets.push(this.buffer.slice(8, 8 + size))
      this.buffer = this.buffer.slice(8 + size)
    }
    return packets
  }
}
