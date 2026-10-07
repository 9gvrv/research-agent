from dataclasses import dataclass, field


@dataclass
class Section:
    heading: str | None
    content: str


@dataclass
class Document:
    url: str
    title: str | None = None
    author: str | None = None
    date: str | None = None

    sections: list[Section] = field(default_factory=list)

    def to_llm(self) -> str:
        """Compact article text: title, source, then sections."""
        parts: list[str] = []

        if self.title:
            parts.append(f"# {self.title}")

        meta: list[str] = []
        if self.author:
            meta.append(f"Author: {self.author}")
        if self.date:
            meta.append(f"Date: {self.date}")
        meta.append(f"Source: {self.url}")
        parts.append("\n".join(meta))

        for section in self.sections:
            content = section.content.strip()
            if not content:
                continue
            if section.heading:
                parts.append(f"## {section.heading}\n\n{content}")
            else:
                parts.append(content)

        return "\n\n".join(parts).strip()

    def __str__(self) -> str:
        return self.to_llm()
