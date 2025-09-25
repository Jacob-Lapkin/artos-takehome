# Artos Coding Assessment

**Background:**

There are lots of documents that a biopharmaceutical company has to write in the process of creating and approving drugs. These documents can be long, time-consuming, and often rote. 

Clinical documents are one such category of documents. Clinical trial protocols are one of the most important documents companies have to write, and these detail how a company plans to determine a drug’s efficacy in humans. You can find examples of a clinical trial protocol on the [clinicaltrials.gov](http://clinicaltrials.gov) database. 

A rote, derivative document of the clinical trial protocol is an Informed Consent Form (ICF), which is something that all individuals must sign before participating in the trial. This ICF details in plain language (8th grade reading level) what the study is about - it’s goals, benefits, risks, and procedures. You can also find ICFs on the [clinicaltrials.gov](http://clinicaltrials.gov) database. 

**Examples:**

| Protocol | ICF |
| --- | --- |
| [AMP_224.PDF](https://file.notion.so/f/f/98ddfe43-a8e0-42c0-8add-89cf6c86c4b1/922f87e7-6cf9-4127-a0ff-c9055ee27d59/AMP_224.pdf?table=block&id=b2129a73-34cc-4186-807d-000ac4f92110&spaceId=98ddfe43-a8e0-42c0-8add-89cf6c86c4b1&expirationTimestamp=1758002400000&signature=CyHkH_H1ZZk53uRsh99gK49wwFL_GPsYRsWosJP5u-4&downloadName=AMP_224.pdf) | [AMP_ICF.pdf](https://file.notion.so/f/f/98ddfe43-a8e0-42c0-8add-89cf6c86c4b1/a76be7cd-06f0-48bf-9ee6-8a079a420583/AMP_ICF.pdf?table=block&id=92623014-bbb0-4e3a-9016-7c5422ad3276&spaceId=98ddfe43-a8e0-42c0-8add-89cf6c86c4b1&expirationTimestamp=1758002400000&signature=YHT7HTshuC2IUWgO10WfqXIog3GHV-CNJnucyXUf2Xw&downloadName=AMP_ICF.pdf) |
| [Tremelumimab_Protocol.pdf](https://file.notion.so/f/f/98ddfe43-a8e0-42c0-8add-89cf6c86c4b1/76c1b822-5c96-4cc0-816a-bc224bd22fae/Tremelumimab_Protocol.pdf?table=block&id=8a9b40c4-745e-44e8-af4a-b197def024e7&spaceId=98ddfe43-a8e0-42c0-8add-89cf6c86c4b1&expirationTimestamp=1758002400000&signature=1__NAdORSy98O_e8ZJisjbmx1QqcYFADwjaGxYO6aBs&downloadName=Tremelumimab_Protocol.pdf) | [Tremelumimab_CTLA4_ICF.pdf](https://file.notion.so/f/f/98ddfe43-a8e0-42c0-8add-89cf6c86c4b1/ab7cb8af-a3be-4bd4-8897-15d918dbfe5d/Tremelimumab_CTLA4_ICF.pdf?table=block&id=8e77342c-a860-40b2-a4db-abeb2abbba98&spaceId=98ddfe43-a8e0-42c0-8add-89cf6c86c4b1&expirationTimestamp=1758002400000&signature=uAxhNpxGvbzO42EihqSb4T2_rZ3LxRzxPHI0AjRtCOA&downloadName=Tremelimumab+CTLA4+ICF.pdf) |
| [E7 Induction Cervical Cancer.pdf](https://file.notion.so/f/f/98ddfe43-a8e0-42c0-8add-89cf6c86c4b1/30d2bcee-516b-416b-95d9-56d08d0fdb98/E7_Induction_Cervical_Cancer.pdf?table=block&id=63463bb7-4830-440c-b53c-6fd987bf2f52&spaceId=98ddfe43-a8e0-42c0-8add-89cf6c86c4b1&expirationTimestamp=1758002400000&signature=-MIWKxch3pVCeUoK2Rr_nu4s5p16kFP1Wyxuq_tqprU&downloadName=E7+Induction+Cervical+Cancer.pdf) | [E7 Screening ICF.pdf](https://file.notion.so/f/f/98ddfe43-a8e0-42c0-8add-89cf6c86c4b1/63c99443-56a4-4820-b5e5-b9e5a401c5cc/E7_Screening_ICF.pdf?table=block&id=ad469e6b-a8ea-496d-82a7-2e62fc6864d2&spaceId=98ddfe43-a8e0-42c0-8add-89cf6c86c4b1&expirationTimestamp=1758002400000&signature=QaVnwLsBEOLX4bSH1qfHhvKGgfS0ZrB0TqUZgDsFaEQ&downloadName=E7+Screening+ICF.pdf) |

**Task:**

Your task will be to generate an Informed Consent Form (ICF) given a clinical trial protocol. You will build a web application that will allow a user to:

1. Upload any clinical trial protocol (in .docx or .pdf) 
2. Generate an Informed Consent Form with headings and appropriate information under each heading. Here is a template for the informed consent form
3. Download this Informed Consent Form as a .docx file 
4. Show in the logs the page number and section of the content used to generate each section of the ICF

Much of an ICF is already templated out – you don’t need to generate every section. Just generate the following: 

- Purpose of the Study
- Study Procedures
    - Include number of patients and duration of the study
- Risks
- Benefits

Here is a template you can use: 

[ICF-template-original.docx](attachment:9e27cf01-a3c9-4dbb-af09-50eaf1c8648a:ICF-template-original.docx)

**Requirements:**

Languages: 

- No specific languages required

LLMs 

- Use whatever LLMs you see fit. If possible, please use your own API keys for this task.

Cloud services (not required) 

- AWS or Azure

Agentic functionality 

- We’re interested in what can be done beyond RAG. Come up with a retrieval strategy that is more robust than semantic similarity search that you think would help solve some of the reliability problems that you observe given the source data provided. Think about things like semantically similar chunks that mean very different things in their respective contexts and distinctions between things that are to be done versus things that have been done, for example.

**Timeline:** 

Please complete this within a 3 days of receiving it. 

**Resources:** 

- Retrieval Augmented Generation (RAG):
    - [Good source from Pinecone](https://www.pinecone.io/learn/retrieval-augmented-generation/)
    - [Simple vs. Complex RAG](https://medium.com/enterprise-rag/an-introduction-to-rag-and-simple-complex-rag-9c3aa9bd017b)
- Prompt Engineering & Orchestration:
    - [LangChain](https://python.langchain.com/docs/get_started/introduction/)
    - [Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering/six-strategies-for-getting-better-results)
- Models:
    - [OpenAI](https://platform.openai.com/docs/models)
    - Claude
- Vector Databases:
    - [FAISS](https://github.com/facebookresearch/faiss)
    - [Pinecone](https://docs.pinecone.io/guides/getting-started/overview)
- Building a Web App:
    - [Create React App](https://create-react-app.dev/)
