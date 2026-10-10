import type { PasswordRequirement } from "@/l/validators";

/**
 * Live checklist of the password policy (`getPasswordRequirements`), shared
 * by every screen that sets a password. Structure only: styling is the
 * project's design decision.
 */
const PasswordRequirements = ({ requirements }: { requirements: PasswordRequirement[] }) => (
  <ul aria-label="Requisitos de la contraseña">
    {requirements.map((requirement) => (
      <li key={requirement.key} data-met={requirement.met}>
        <span aria-hidden="true">{requirement.met ? "✓" : "•"}</span> {requirement.label}
      </li>
    ))}
  </ul>
);

export default PasswordRequirements;
