import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EmptyPanel, ErrorPanel, LoadingPanel } from './StatePanel'

describe('data states', () => {
  it('explains when selected data is unavailable', () => {
    render(<EmptyPanel title="No mapped stations">No station coordinates match this city.</EmptyPanel>)
    expect(screen.getByRole('heading', { name: 'No mapped stations' })).toBeInTheDocument()
    expect(screen.getByText('No station coordinates match this city.')).toBeInTheDocument()
  })

  it('announces failed API requests', () => {
    render(<ErrorPanel message="Backend not connected" />)
    expect(screen.getByRole('alert')).toHaveTextContent('Backend not connected')
  })

  it('exposes a loading status', () => {
    render(<LoadingPanel label="Loading records" />)
    expect(screen.getByText('Loading records')).toBeInTheDocument()
  })
})
