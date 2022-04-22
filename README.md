
Corpus Utilities
================================

- Convert 2022 n2c2 Track 2 Social Determinants of Health Corpus into SHARPn and OMOP CDM
  - convert-n2c2-sdoh-brat-to-sharpn.py
  - convert-n2c2-sdoh-brat-to-omop-cdm.py
- Augment 2019 n2c2 Track 3 Corpus with Lab Name/Lab Value relations (patch_2019_n2c2_track-3_corpus.py) **AMAI Summit 2021**
- Line Reshaper (line_reshaper.py)
- NLM Scrubber to brat Format (nlm2brat.py)
- Split 2006 i2b2 Corpus into Files (split_2006_corpus_int_files.py)


Convert 2022 n2c2 Track 2 Social Determinants of Health Corpus into SHARPn and OMOP CDM
=======================================================================================

See the ``README.rst`` in the ``n2c2`` folder


Augment 2019 n2c2 Track 3 Corpus with Lab Name/Lab Value relations
==================================================================

**AMAI Summit 2021**

See the ``README.rst`` in the ``n2c2`` folder and the related redacted
corpus:
https://github.com/MUSC-TBIC/2010-i2b2-VA-Challenge-Corpus-Augmentations


Line Reshaper
===============

First, you'll probably want to gather general descriptive stats about the line shapes.

The sample corpus I'm working with was provided as part of the i2b2 2016 NLP challenge and can be downloaded here:
- https://www.i2b2.org/NLP/RDoCforPsychiatry
- https://www.i2b2.org/NLP/DataSets/Main.php

```shell
python3 line_reshaper.py \
	--input ${I2B2_2016_TRACK1}/training-text/ \
	--print-metrics

Files:	600
Lines:	90245
Min:	1
Mean:	80.8518809906366
Median:	46
Max:	3709
```

Providing an output folder writes a copy of every file with a max fixed width on all lines (default = 80).

```shell
python3 line_reshaper.py \
	--input ${I2B2_2016_TRACK1}/training-text/ \
	--output ${MUNGED_OUT}/fixed_width

python3 line_reshaper.py \
	--input ${MUNGED_OUT}/fixed_width \
	--print-metrics

Files:	600
Lines:	144050
Min:	1
Mean:	50.2732176327664
Median:	54.0
Max:	80
```

You can set the max fixed width to any value using the `--max-width` argument.

```shell
python3 line_reshaper.py \
  --max-width 45 \
	--input ${I2B2_2016_TRACK1}/training-text/ \
	--output ${MUNGED_OUT}/fixed_width_45

python3 line_reshaper.py \
	--input ${MUNGED_OUT}/fixed_width_45 \
	--print-metrics

Files:	600
Lines:	215560
Min:	1
Mean:	33.25959825570607
Median:	39.0
Max:	45
```

Setting the `--max-width` to negative one (`-1`) generates a file with exactly one line.

```shell
python3 line_reshaper.py \
  --max-width -1 \
	--input ${I2B2_2016_TRACK1}/training-text/ \
	--output ${MUNGED_OUT}/one_line

python3 line_reshaper.py \
	--input ${MUNGED_OUT}/one_line \
	--print-metrics

Files:	600
Lines:	600
Min:	2177
Mean:	12374.743333333334
Median:	12089.0
Max:	28949
```

NLM Scrubber to brat Format
==============================

```
python3.7 nlm2brat.py \
  --raw-dir ${CORPUS_DIR}/test-text \
  --processed-dir ${CORPUS_DIR}/test/nphi_out \
  --output-dir ${CORPUS_DIR}/test/brat
```

Split 2006 i2b2 Corpus into Files
=============================================

*NB* - This script doesn't work on the de-identification training
corpus because of a tag mis-match.  We'll need to handle that in a
later release. It should work fine on the test corpus and both smoking
corpora.

```
python3 split_2006_corpus_into_files.py \
  --input $CORPUS2006/annotated_testing_deid.xml \
  --output $CORPUS2006/test/xml

ls $CORPUS2006/test/xml
056.xml
111.xml
135.xml
151.xml
168.xml
177.xml
185.xml
194.xml
202.xml
206.xml
...

```
