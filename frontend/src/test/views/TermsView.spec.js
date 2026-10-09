import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import TermsView from '@/views/TermsView.vue'

const backMock = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({
    back: backMock,
  }),
}))

function mountView() {
  return mount(TermsView, {
    global: {
      stubs: {
        HeaderLayout: {
          template: `<header><button data-test="header-back" @click="$emit('click:title')">title</button></header>`,
        },
      },
    },
  })
}

describe('TermsView', () => {
  it('renders the static copy for terms and conditions', () => {
    const wrapper = mountView()
    expect(wrapper.text()).toContain('Terms & Conditions')
    expect(wrapper.text()).toContain('Last updated: October 2025')
  })

  it('leaves the page when either back control is clicked', async () => {
    const wrapper = mountView()

    await wrapper.get('.back-btn').trigger('click')
    expect(backMock).toHaveBeenCalledTimes(1)

    await wrapper.get('[data-test="header-back"]').trigger('click')
    expect(backMock).toHaveBeenCalledTimes(2)
  })
})
