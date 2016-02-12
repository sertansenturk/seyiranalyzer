import numpy as np
import PitchDistribution
import matplotlib.pyplot as plt

class AudioSeyirAnalyzer():
    _version = "0.1"
    _slug = "makamseyir"

    def __init__(self, kernel_width = 7.5, step_size=7.5):
        self.kernel_width = kernel_width
        self.step_size = step_size

        self.dummy_ref_freq = 440.0  # hz

    def getSettings(self):
      citation = u"Bozkurt"
      
      return {'kernel_width': self.kernel_width, 'step_size': self.step_size,
              'citation': citation}

    def compute_seyir_features_per_interval(self, pp, tt, t_intervals):
        seyir_features = []
        maxdur = 0
        for ti in t_intervals:
            dur = ti[1] - ti[0]
            if dur > maxdur:
                maxdur = dur

        for ti in t_intervals:
            p_sliced = [p for t, p in zip(tt, pp) 
                if ti[1] > t >= ti[0]]

            p_cent = PitchDistribution.hz_to_cent(p_sliced, self.dummy_ref_freq)

            if p_cent.size == 0:  # silence 
                seyir_features.append({'pitch_distribution':[],'stable_pitches':[],
                    'average_pitch':np.nan, 'time_interval':ti})
            else:
                pd = PitchDistribution.generate_pd(p_cent, ref_freq=self.dummy_ref_freq,
                    kernel_width=self.kernel_width, step_size=self.step_size)

                # reconvert to Hz
                pd.bins = PitchDistribution.cent_to_hz(pd.bins, pd.ref_freq)
                pd.ref_freq = []

                # normalize to 1 (instead of the area under the curve)
                maxval = max(pd.vals)
                numRatio = float(len(p_cent))/len(p_sliced) # ratio of number of samples
                timeRatio = (ti[1]-ti[0])/maxdur
                pd.vals = pd.vals*numRatio*timeRatio/maxval

                # get the stable pitches, i.e. peaks
                peak_idx, peak_vals = pd.detect_peaks()
                stable_pitches = [{'frequency':pd.bins[idx], 'value':val} 
                    for idx, val in zip(peak_idx, peak_vals)]

                # get the average pitch
                avpitch = PitchDistribution.cent_to_hz(np.mean(p_cent), self.dummy_ref_freq)

                seyir_features.append({'pitch_distribution':pd,'stable_pitches':stable_pitches,
                    'average_pitch':avpitch, 'time_interval':ti})

        return seyir_features

    def analyze(self, pitch, frame_size = 20.0, hop_ratio = 0.5):
        hop_size = frame_size*hop_ratio

        pitch = np.array(pitch)
        tt = pitch[:,0]
        pp = pitch[:,1]

        tb = 0
        t_intervals = []
        while tb < tt[-1]:
            t_intervals.append([tb, min([tb+frame_size, tt[-1]])])
            tb += hop_size

        return self.compute_seyir_features_per_interval(pp, tt, t_intervals)

    @staticmethod
    def plot(seyir_features, plot_average_pitch=True, plot_stable_pitches=True,
             plot_distribution=False):

        if plot_distribution:
            time_starts = [sf['time_interval'][0] for sf in seyir_features]
            min_time = min(np.diff(time_starts))
            for sf in seyir_features:
                if sf['pitch_distribution']:  # ignore silent frame
                    # plot the distributions through time
                    yy = sf['pitch_distribution'].bins
                    tt = sf['time_interval'][0] + sf['pitch_distribution'].vals * min_time*2
                    plt.plot(tt, yy)

        if plot_stable_pitches:
            num_frames = len(seyir_features)
            for sf in seyir_features:
                if sf['stable_pitches']:  # ignore silent frame
                    t_st = sf['time_interval'][0]
                    max_peak = max([sp['value'] for sp in sf['stable_pitches']])
                    for sp in sf['stable_pitches']:
                        clr = 'r' if sp['value'] == max_peak else 'b'
                        # map the values from 0-1 to 1-6
                        marker_thickness = (sp['value']*5+1)*100/num_frames
                        plt.plot(t_st, sp['frequency'], 'o', color = clr, ms=marker_thickness)

        if plot_average_pitch:
            tt = [sf['time_interval'][0] for sf in seyir_features]
            pp = [sf['average_pitch'] for sf in seyir_features]

            plt.plot(tt, pp, color='k', linewidth=3)

        plt.xlim([seyir_features[0]['time_interval'][0], 
            seyir_features[-1]['time_interval'][1]])
        plt.xlabel('Time (sec)')
        plt.ylabel('Frequency (Hz)')
