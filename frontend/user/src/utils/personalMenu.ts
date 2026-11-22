export const defaultPersonalSections = ['overview', 'orders', 'security', 'profile']

export function isPersonalSectionVisible(key: string, config: unknown): boolean {
  const sections = (config as { enabled_sections?: unknown } | null)?.enabled_sections
  return (Array.isArray(sections) ? sections : defaultPersonalSections).includes(key)
}
