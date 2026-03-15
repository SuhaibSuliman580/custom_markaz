/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { cookie } from '@web/core/browser/cookie';
import { GraphRenderer } from '@web/views/graph/graph_renderer';
import { SEP } from '@web/views/graph/graph_model';
import { DEFAULT_BG, getColor, hexToRGBA } from '@web/core/colors/colors';

const NO_DATA = _t('No data');

/**
 * Used to avoid too long legend items.
 * @param {string} label
 * @returns {string} shortened version of the input label
 */
function shortenLabel(label) {
    // string returned could be wrong if a groupby value contain a " / "!
    const groups = label.toString().split(SEP);
    let shortLabel = groups.slice(0, 3).join(SEP);
    if (shortLabel.length > 30) {
        shortLabel = `${shortLabel.slice(0, 30)}...`;
    } else if (groups.length > 3) {
        shortLabel = `${shortLabel}${SEP}...`;
    }
    return shortLabel;
}

/**
 * Used to generate the min/max value of the grid (line & bar charts).
 * The purpose is to keep a bit of space between the lowest/highest data
 * and the bottom/top of the grid.
 * @param {Object[]} datasets
 * @param {Boolean} isStacked
 * @returns {{ min: number, max: number }}
 */
function getMinMaxValue(datasets, isStacked) {
    const values = [];
    if (isStacked) {
        datasets.forEach((dataset) => {
            dataset.data.forEach((value, index) => {
                values[index] = (values[index] || 0) + value;
            });
        });
    } else {
        datasets.forEach((dataset) => {
            dataset.data.forEach((value) => {
                values.push(value);
            });
        });
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    return {
        min: min < 0 ? 1.1 * min : 0.9 * min,
        max: max < 0 ? 0.9 * max : 1.1 * max,
    };
}

patch(GraphRenderer.prototype, {
    getBarChartData() {
        const data = super.getBarChartData();

        data['datasets'].forEach((dataset) => {
            if (dataset.order != -1) {
                dataset.barPercentage = 0.55;
                dataset.borderRadius = 4;
            }
        });

        return data;
    },

    getLineChartData() {
        const data = super.getLineChartData();
        const scheme = cookie.get('color_scheme');

        const { stacked, cumulated } = this.model.metaData;

        for (let index = 0; index < data.datasets.length; ++index) {
            const dataset = data.datasets[index];
            dataset.pointBorderWidth = 2.5;
            dataset.pointHoverBorderWidth = 2.5;
            dataset.pointBackgroundColor = scheme == 'dark' ? '#2a2b2d' : '#ffffff';
            dataset.pointBorderColor = dataset.borderColor;
            dataset.cubicInterpolationMode = 'monotone';
            if (stacked) {
                dataset.backgroundColor = dataset.borderColor;
            }

            if (stacked && !cumulated) {
                const { height } = this.containerRef.el.getBoundingClientRect();
                const x2d = this.canvasRef.el.getContext('2d');
                const o = x2d.createLinearGradient(0, 0, 0, height * 0.9);
                o.addColorStop(0, dataset.backgroundColor);
                o.addColorStop(1, hexToRGBA(dataset.backgroundColor, 0.0072));
                dataset.backgroundColor = o;
                dataset.fill = true;
            }
        }

        return data;
    },

    getElementOptions() {
        const elementOptions = super.getElementOptions();
        if (elementOptions.line) {
            elementOptions.line.borderWidth = 2.5;
        }

        elementOptions.point = {
            pointStyle: 'circle',
            radius: 5,
            hoverRadius: 7,
            borderWidth: 3,
            hoverBorderWidth: 3,
            backgroundColor: '#fff',
            hoverBackgroundColor: '#fff',
        }

        return elementOptions;
    },

    getLegendOptions() {
        const legendOptions = super.getLegendOptions();
        const scheme = cookie.get('color_scheme');
        const fontColor = scheme === 'dark' ? '#fff' : '#000';
        const { mode } = this.model.metaData;

        if (mode === 'pie') {
            legendOptions.labels = {
                generateLabels: (chart) => {
                    const data = chart.data;
                    if (data.labels.length && data.datasets.length) {
                        return data.labels.map((label, i) => {
                            return {
                                index: i,
                                text: shortenLabel(label),
                                fullText: label,
                                hidden: !chart.getDataVisibility(i),
                                fillStyle: label === NO_DATA ? DEFAULT_BG : getColor(i, scheme),
                                strokeStyle: data.datasets[0]['backgroundColor'][i],
                                fontColor: fontColor,
                                lineWidth: 0,
                            };
                        });
                    }
                    return [];
                }
            }
        }
        else {
            legendOptions.position = 'top';
            legendOptions.align = 'end';
            const superGenerator = legendOptions.labels.generateLabels;
            legendOptions.labels = {
                generateLabels: (chart) => {
                    const labels = superGenerator(chart).map((vals) => {
                        const label = {
                            ...vals,
                            fontColor: fontColor,
                        };
                        return label;
                    });
                    return labels;
                },
            };
        }

        return legendOptions;
    },

    getScaleOptions() {
        const scaleOptions = super.getScaleOptions();

        const { datasets } = this.model.data;
        const { stacked } = this.model.metaData;
        if (scaleOptions.x && scaleOptions.y) {
            scaleOptions.x.grid = {
                display: false,
            }
            scaleOptions.x.border = {
                display: false,
            }

            const { min: suggestedMin, max: suggestedMax } = getMinMaxValue(datasets, stacked);

            scaleOptions.y.beginAtZero = true;
            scaleOptions.y.suggestedMin = suggestedMin;
            scaleOptions.y.suggestedMax = suggestedMax;
            scaleOptions.y.border = {
                display: false,
            }
        }

        return scaleOptions;
    },

    prepareOptions() {
        const options = super.prepareOptions();

        const { mode } = this.model.metaData;
        options.animation = this.getAnimationOptions();
        if (mode === 'line') {
            options.interaction = {
                mode: 'index',
                intersect: false,
            };
        }
        if (mode === 'pie') {
            options.radius = '90%';
        }
        options.onResize = () => {
            this.resizeChart(options);
        }
        return options;
    },

    /**
     * Adapt Pie chart layout on mobile
     * @param {Object} context
     */
    resizeChart(context) {
        const { mode } = this.model.metaData;
        if (mode === 'pie') {
            if (this.env.isSmall) {
                context.plugins.legend.position = 'bottom';
                context.plugins.legend.align = 'center';
            } else {
                context.plugins.legend.position = 'right';
                context.plugins.legend.align = 'start';
            }
        }
    },

    /**
     * Returns the animation options.
     * 1. This adds progressive animation for Bar & Line charts.
     * 2. Reduce animation duration for Pie chart.
     * @returns {Object}
     */
    getAnimationOptions() {
        let delayed;
        const { mode } = this.model.metaData;
        const labelsCount = this.model.data.labels.length;
        const gap = 350;
        const animationOptions = {};
        if (mode === 'pie') {
            animationOptions.offset = { duration: 200 };
        } else {
            animationOptions.duration = 600;
            animationOptions.onComplete = () => {
                delayed = true;
            };
            animationOptions.delay = (context) => {
                let delay = 0;
                if ((mode === 'bar' || mode === 'line') && !delayed) {
                    delay = context.dataIndex * (gap / labelsCount);
                }
                return delay;
            };
        }
        return animationOptions;
    }
});
