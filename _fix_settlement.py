import pathlib

fp = pathlib.Path(r'c:\Vibe Project\Songyan\src\songyan\workflows\_nodes.py')
lines = fp.read_text(encoding='utf-8').splitlines(keepends=True)

# Find function boundaries
func_start = None
func_end = None
for i, line in enumerate(lines):
    if 'async def settlement_extractor_node' in line:
        func_start = i
    if func_start is not None and i > func_start + 10 and line.strip() == '' and 'async def' in lines[i+1] if i+1 < len(lines) else False:
        func_end = i
        break

# Find key lines within function (0-indexed)
# After function insertion in phase1, function is at lines 1345-1512 approximately
# Let's use text matching instead

# Step 1: Add summary_id = None after settlement_needs_review = False
for i, line in enumerate(lines):
    if line.strip() == 'settlement_needs_review = False':
        lines.insert(i+1, '    summary_id = None\n')
        break

# Step 2: Insert skip_settlement block after the blank line following settlement_needs_review
for i, line in enumerate(lines):
    if line.strip() == 'settlement_needs_review = False':
        # find next blank line
        j = i + 1
        while j < len(lines) and lines[j].strip() != '':
            j += 1
        # Insert if block and else after this blank line
        q = chr(34)
        block = [
            '    # Task 108: 支持跳过 settlement（如 convergence_failed 路径）\n',
            '    if state.get(' + q + '_skip_settlement' + q + ', False):\n',
            '        logger.info(\n',
            '            ' + q + 'settlement_extractor_node.skipping_settlement' + q + ',\n',
            '            project_id=state[' + q + 'project_id' + q + '],\n',
            '            chapter_number=state[' + q + 'chapter_number' + q + '],\n',
            '            version_id=version.version_id,\n',
            '        )\n',
            '        # Fallback inline summary\n',
            '        summary_id = new_id(' + q + 'sum' + q + ')\n',
            '        _content = version.content\n',
            '        _summary_text = _content[:300] + ' + q + '...' + q + ' if len(_content) > 300 else _content\n',
            '        fallback_summary = ChapterSummary(\n',
            '            summary=_summary_text,\n',
            '            chapter_number=state[' + q + 'chapter_number' + q + '],\n',
            '            key_events=[],\n',
            '            characters_appeared=[],\n',
            '            emotional_tone=' + q + q + ',\n',
            '            impact_score=0.0,\n',
            '        )\n',
            '        try:\n',
            '            await SummaryRepository().create(fallback_summary, state[' + q + 'project_id' + q + '], summary_id)\n',
            '        except Exception as exc:\n',
            '            logger.warning(\n',
            '                ' + q + 'settlement_extractor_node.fallback_summary_failed' + q + ',\n',
            '                error=str(exc),\n',
            '                project_id=state[' + q + 'project_id' + q + '],\n',
            '                chapter_number=state[' + q + 'chapter_number' + q + '],\n',
            '            )\n',
            '            summary_id = None\n',
            '    else:\n',
        ]
        for k, l in enumerate(block):
            lines.insert(j+1+k, l)
        break

# Step 3: Indent lines inside else block
# We need to indent from '# 1. 提取' through the summary block until just before '# 3. RAG'
# Find the else: line first
else_idx = None
for i, line in enumerate(lines):
    if line.strip() == 'else:':
        else_idx = i
        break

# Find start of extract block (the line after else:)
extract_start = else_idx + 1

# Find end of summary block: the blank line before '# 3. RAG'
rag_idx = None
for i in range(else_idx+1, len(lines)):
    if lines[i].strip().startswith('# 3. RAG'):
        rag_idx = i
        break

# The block to indent is from extract_start to rag_idx-1
for i in range(extract_start, rag_idx):
    if lines[i] != '\n':
        lines[i] = '    ' + lines[i]

# Step 4: Remove duplicate summary_id = None inside the else block
# It was at line 1402 originally, now shifted. Find it inside the else block.
for i in range(extract_start, rag_idx):
    if lines[i].strip() == 'summary_id = None':
        del lines[i]
        break

# Step 5: Fix return statement - settlement_id should be None when skip_settlement is true
for i, line in enumerate(lines):
    if line.strip().startswith('"settlement_id": new_id("st")'):
        lines[i] = line.replace('new_id("st") if settlement is not None else None', 'None if settlement is None and state.get("_skip_settlement", False) else (new_id("st") if settlement is not None else None)')
        break

fp.write_text(''.join(lines), encoding='utf-8')
print('settlement fix done')
