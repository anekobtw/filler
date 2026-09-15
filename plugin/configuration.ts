import rawConfig from "../resume.config.json";

export type FieldRule = {
  keywords: string[];
  value: string;
  inputTypes?: string[];
  priority?: number;
  selectPartialMatch?: boolean;
};

export type ResumeConfig = {
  overwriteExisting?: boolean;
  fields: FieldRule[];
};

export type Question = {
  label: string;
  type?: "date" | "email" | "tel" | "url";
};

const rules: Omit<FieldRule, "value">[] = [
  { keywords: ["first name", "given name", "forename", "fname"] },
  { keywords: ["last name", "family name", "surname", "lname"] },
  { keywords: ["full name", "your name", "name"] },
  { keywords: ["school email", "university email", "college email", "academic email", "student email", "institutional email", "edu email"], priority: 1 },
  { keywords: ["email", "email address"] },
  { keywords: ["phone", "telephone", "mobile"] },
  { keywords: ["linkedin", "linkedin url"] },
  { keywords: ["portfolio", "website", "personal site"] },
  { keywords: ["location", "city", "current location"] },
  { keywords: ["school", "university", "college", "institution"] },
  { keywords: ["degree", "qualification"], selectPartialMatch: true },
  { keywords: ["discipline", "major", "field of study", "area of study"] },
  { keywords: ["start date"], inputTypes: ["date"] },
  { keywords: ["start date year", "start year"], inputTypes: ["number", "text"] },
  { keywords: ["start month", "start date month"], selectPartialMatch: true },
  { keywords: ["end date", "graduation date"], inputTypes: ["date"] },
  { keywords: ["end date year", "end year", "graduation year"], inputTypes: ["number", "text"] },
  { keywords: ["end month", "end date month", "graduation month"], selectPartialMatch: true },
  { keywords: ["work authorization", "authorized to work", "legally authorized", "eligible to work", "eligible to work in united states", "work in united states"] },
  { keywords: ["gender"] },
  { keywords: ["race", "racial identity"] },
  { keywords: ["pronouns", "personal pronouns"] },
  { keywords: ["military veteran", "veteran status", "protected veteran", "veteran"] },
  { keywords: ["disability", "disability status", "disabled"] },
  { keywords: ["require sponsorship", "need sponsorship", "visa sponsorship"] },
];

export const questions: Question[] = [
  { label: "First name" }, { label: "Last name" }, { label: "Full name" },
  { label: "School email", type: "email" }, { label: "Email", type: "email" }, { label: "Phone", type: "tel" },
  { label: "LinkedIn URL", type: "url" }, { label: "Portfolio URL", type: "url" }, { label: "Location" },
  { label: "School or university" }, { label: "Degree" }, { label: "Field of study" },
  { label: "Education start date", type: "date" }, { label: "Education start year" }, { label: "Education start month" },
  { label: "Education end date", type: "date" }, { label: "Graduation year" }, { label: "Graduation month" },
  { label: "Authorized to work" }, { label: "Gender" }, { label: "Race" },
  { label: "Pronouns" }, { label: "Veteran status" }, { label: "Disability status" }, { label: "Require sponsorship" },
];

export function blankConfig(): ResumeConfig {
  return { fields: rules.map((rule) => ({ ...rule, value: "" })) };
}

function cloneConfig(config: ResumeConfig): ResumeConfig {
  return {
    overwriteExisting: config.overwriteExisting,
    fields: config.fields.map((field) => ({
      ...field,
      keywords: [...field.keywords],
      inputTypes: field.inputTypes ? [...field.inputTypes] : undefined,
    })),
  };
}

export function initialConfig(): ResumeConfig {
  return isResumeConfig(rawConfig)
    ? withoutGenderIdentity(cloneConfig(rawConfig))
    : blankConfig();
}

function withoutGenderIdentity(config: ResumeConfig): ResumeConfig {
  return {
    ...config,
    fields: config.fields.filter(
      (field) => !field.keywords.includes("gender identity"),
    ),
  };
}

export function currentConfig(value: unknown): ResumeConfig {
  return isResumeConfig(value) ? withoutGenderIdentity(value) : initialConfig();
}

export function isResumeConfig(value: unknown): value is ResumeConfig {
  return (
    typeof value === "object" &&
    value !== null &&
    "fields" in value &&
    Array.isArray(value.fields) &&
    value.fields.every(
      (field) =>
        typeof field === "object" &&
        field !== null &&
        "value" in field &&
        typeof field.value === "string",
    )
  );
}
