


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
