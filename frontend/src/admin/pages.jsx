import CrudTable from './CrudTable.jsx'

export const AgeBandsPage = () => (
  <CrudTable resource="age-bands" title="Age bands" fields={[
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'min_age', label: 'Min', type: 'number' },
    { key: 'max_age', label: 'Max', type: 'number' },
    { key: 'description', label: 'Description', type: 'text' },
    { key: 'pedagogy_notes', label: 'Pedagogy notes', type: 'json' },
  ]} />
)

export const CoursesPage = () => (
  <CrudTable resource="courses" title="Courses" fields={[
    { key: 'age_band_id', label: 'Age band UUID', type: 'text' },
    { key: 'subject', label: 'Subject', type: 'text' },
    { key: 'title', label: 'Title', type: 'text' },
    { key: 'description', label: 'Description', type: 'text' },
  ]} />
)

export const UnitsPage = () => (
  <CrudTable resource="units" title="Units" fields={[
    { key: 'course_id', label: 'Course UUID', type: 'text' },
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'description', label: 'Description', type: 'text' },
    { key: 'order_index', label: 'Order', type: 'number' },
  ]} />
)

export const SkillsPage = () => (
  <CrudTable resource="skills" title="Skills" fields={[
    { key: 'unit_id', label: 'Unit UUID', type: 'text' },
    { key: 'code', label: 'Code', type: 'text' },
    { key: 'name', label: 'Name', type: 'text' },
    { key: 'description', label: 'Description', type: 'text' },
    { key: 'order_index', label: 'Order', type: 'number' },
    { key: 'p_init', label: 'p_init', type: 'number' },
    { key: 'p_transit', label: 'p_transit', type: 'number' },
    { key: 'p_slip', label: 'p_slip', type: 'number' },
    { key: 'p_guess', label: 'p_guess', type: 'number' },
    { key: 'prerequisites', label: 'Prereqs (JSON list)', type: 'json' },
  ]} />
)

export const ExercisesPage = () => (
  <CrudTable resource="exercises" title="Exercises" fields={[
    { key: 'skill_id', label: 'Skill UUID', type: 'text' },
    { key: 'type', label: 'Type', type: 'select', options: [
      { value: 'MULTIPLE_CHOICE', label: 'Multiple choice' },
      { value: 'FREE_RESPONSE', label: 'Free response' },
      { value: 'DRAG_DROP', label: 'Drag-drop' },
      { value: 'SHORT_ANSWER', label: 'Short answer' },
    ]},
    { key: 'prompt', label: 'Prompt', type: 'text' },
    { key: 'payload', label: 'Payload (JSON)', type: 'json' },
    { key: 'difficulty', label: 'Difficulty', type: 'number' },
    { key: 'locale', label: 'Locale', type: 'text' },
  ]} />
)
