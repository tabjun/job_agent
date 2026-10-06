"""Extract explicitly selected DOCX sources and compile an evidence-linked draft."""

import argparse
import hashlib
import json
from pathlib import Path

from resume_source import read_docx_paragraphs
from site_form_mapper import default_sites


def extract_sources(paths):
    sources = []
    seen = set()
    for raw in paths:
        path = Path(raw).resolve()
        if path.suffix.lower() != '.docx':
            raise ValueError('Only explicitly selected DOCX sources are supported')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        sources.append({
            'id': f'source_{len(sources) + 1}', 'file': str(path),
            'sha256': digest, 'paragraphs': read_docx_paragraphs(path),
        })
    if not sources:
        raise ValueError('Select at least one readable source')
    return {'sources': sources}


def compile_draft(corpus, draft):
    sources = {}
    for source in corpus['sources']:
        if source['id'] in sources:
            raise ValueError('Duplicate source id')
        if hashlib.sha256(Path(source['file']).read_bytes()).hexdigest() != source['sha256']:
            raise ValueError('Source changed; extract and review again')
        if read_docx_paragraphs(source['file']) != source['paragraphs']:
            raise ValueError('Extracted evidence differs from source')
        sources[source['id']] = source
    values, evidence = {}, {}
    for block in draft['blocks']:
        key = block['field']
        if key in values or not isinstance(block['text'], str) or not block['text'].strip():
            raise ValueError('Duplicate field or empty draft text')
        if not block.get('evidence'):
            raise ValueError(f'No source evidence for {key}')
        citations = []
        for ref in block['evidence']:
            source = sources.get(ref['source_id'])
            if source is None:
                raise ValueError('Unknown source reference')
            rows = {row['paragraph_index']: row for row in source['paragraphs']}
            for index in ref['paragraph_indices']:
                if index not in rows:
                    raise ValueError('Unknown paragraph reference')
                citations.append({'source_id': source['id'], 'paragraph_index': index, 'text': rows[index]['text']})
        if not citations:
            raise ValueError('Empty evidence reference')
        values[key] = block['text']
        evidence[key] = citations
    if not values:
        raise ValueError('Draft contains no blocks')
    return {'field_values': values, 'source_evidence': evidence,
            'generation_method': 'human_reviewed_evidence_linked_draft',
            'review_notes': draft.get('review_notes', [])}


def save_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Explicit DOCX library and reviewed resume draft')
    sub = parser.add_subparsers(dest='command', required=True)
    extract = sub.add_parser('extract')
    extract.add_argument('--source', action='append', required=True)
    extract.add_argument('--output-dir', default='result/resume_library')
    build = sub.add_parser('build')
    build.add_argument('--corpus', required=True)
    build.add_argument('--draft', required=True)
    build.add_argument('--output-dir', default='result/master_resume')
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if args.command == 'extract':
        corpus = extract_sources(args.source)
        save_json(output / 'corpus.json', corpus)
        for source in corpus['sources']:
            (output / f"{source['id']}.md").write_text('\n\n'.join(
                f"[{row['paragraph_index']}] {row['text']}" for row in source['paragraphs']) + '\n', encoding='utf-8')
        print(f"Extracted {len(corpus['sources'])} explicitly selected sources")
    else:
        corpus = json.loads(Path(args.corpus).read_text(encoding='utf-8'))
        draft = json.loads(Path(args.draft).read_text(encoding='utf-8'))
        package = compile_draft(corpus, draft)
        save_json(output / 'master_resume.json', {'package': package})
        (output / 'master_resume.md').write_text('\n\n'.join(
            f"## {block.get('heading', block['field'])}\n\n{block['text']}" for block in draft['blocks']) + '\n', encoding='utf-8')
        for site in default_sites():
            save_json(output / f'{site}_package.json', {'site': site, 'package': package})
        print(f"Compiled {len(package['field_values'])} reviewed fields for {len(default_sites())} sites")


if __name__ == '__main__':
    main()
