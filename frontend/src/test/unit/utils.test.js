import { describe, it, expect } from 'vitest'
import { cn } from '@/lib/utils'

describe('utils: cn', () => {
  it('joins truthy class names', () => {
    expect(cn('btn', undefined, null, 'primary')).toBe('btn primary')
  })

  it('applies tailwind merge conflict resolution', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
  })
})
