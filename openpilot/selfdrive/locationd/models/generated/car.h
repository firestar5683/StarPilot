#pragma once
#include "rednose/helpers/ekf.h"
extern "C" {
void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea);
void car_err_fun(double *nom_x, double *delta_x, double *out_4453381878183487431);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_875318933667132564);
void car_H_mod_fun(double *state, double *out_8397482359330457307);
void car_f_fun(double *state, double dt, double *out_133753830955943846);
void car_F_fun(double *state, double dt, double *out_7906645124566014609);
void car_h_25(double *state, double *unused, double *out_1042419833926058116);
void car_H_25(double *state, double *unused, double *out_5254430871451225200);
void car_h_24(double *state, double *unused, double *out_858315406556051163);
void car_H_24(double *state, double *unused, double *out_5344959191384304354);
void car_h_30(double *state, double *unused, double *out_6160796123059927854);
void car_H_30(double *state, double *unused, double *out_7772763829958473827);
void car_h_26(double *state, double *unused, double *out_7284274682988778117);
void car_H_26(double *state, double *unused, double *out_1512927552577168976);
void car_h_27(double *state, double *unused, double *out_557704697785718655);
void car_H_27(double *state, double *unused, double *out_1448028770476807909);
void car_h_29(double *state, double *unused, double *out_5886906433235774616);
void car_H_29(double *state, double *unused, double *out_1236965885638009186);
void car_h_28(double *state, double *unused, double *out_7336233453404305132);
void car_H_28(double *state, double *unused, double *out_3200596157203335437);
void car_h_31(double *state, double *unused, double *out_767225771641552227);
void car_H_31(double *state, double *unused, double *out_886719450343817500);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}