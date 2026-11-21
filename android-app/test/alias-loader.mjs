const phonekbSppStubUrl = new URL('./phonekb-spp-stub.mjs', import.meta.url).href

export async function resolve(specifier, context, nextResolve) {
  if (specifier === '@/uni_modules/phonekb-spp') {
    return { url: phonekbSppStubUrl, shortCircuit: true }
  }
  return nextResolve(specifier, context)
}
