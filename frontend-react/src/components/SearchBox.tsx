import { useState } from 'react'
import type { FormEvent } from 'react'

type Props = {
  query: string
  setQuery: (value: string) => void
  onSubmit: () => void
  large?: boolean
  placeholder?: string
}

export function SearchBox({ query, setQuery, onSubmit, large = false, placeholder = 'Busca productos: arroz, leche, café…' }: Props) {
  const [focused, setFocused] = useState(false)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (query.trim().length >= 2) onSubmit()
  }

  return (
    <form
      className={`search-box${large ? ' search-box-large' : ''}${focused ? ' focused' : ''}`}
      onSubmit={handleSubmit}
      role="search"
    >
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder={placeholder}
        aria-label="Buscar productos"
      />
      <button type="submit">Buscar</button>
    </form>
  )
}
