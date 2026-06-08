# Forestry Report Request

Topic: 智慧林务系统建设计划书

Document type: proposal

Audience: 项目负责人、技术评审、林业主管部门信息化负责人

Target length: 5000字

Style: 正式、技术导向、少空话，突出建设目标、系统架构、实施路径和风险控制

Constraints:

- 需要覆盖现状痛点、建设目标、核心功能、数据治理、实施计划、验收指标和风险应对
- 不能编造政策条文、预算数字或已有系统数据
- 如果资料不足，需要明确标注“依据不足”
- 输出格式优先使用 Markdown，便于后续转 docx

Example command:

```bash
writing-agent run \
  --topic "智慧林务系统建设计划书" \
  --type proposal \
  --audience "项目负责人和技术评审" \
  --length "5000字" \
  --style "正式、技术导向、少空话" \
  --source ./data/forestry_notes.md
```

