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
void car_err_fun(double *nom_x, double *delta_x, double *out_7126582961958922662);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_945533236592444203);
void car_H_mod_fun(double *state, double *out_2778542718740683729);
void car_f_fun(double *state, double dt, double *out_3017733201534411708);
void car_F_fun(double *state, double dt, double *out_9105766054919985506);
void car_h_25(double *state, double *unused, double *out_614805040009735499);
void car_H_25(double *state, double *unused, double *out_2273208276540387017);
void car_h_24(double *state, double *unused, double *out_217533166938587881);
void car_H_24(double *state, double *unused, double *out_1728503802090121616);
void car_h_30(double *state, double *unused, double *out_13386882396371945);
void car_H_30(double *state, double *unused, double *out_4643482064951229738);
void car_h_26(double *state, double *unused, double *out_4988286385264473700);
void car_H_26(double *state, double *unused, double *out_6014711595414443241);
void car_h_27(double *state, double *unused, double *out_5616478307670581144);
void car_H_27(double *state, double *unused, double *out_2468718753150804827);
void car_h_29(double *state, double *unused, double *out_8968582289610468820);
void car_H_29(double *state, double *unused, double *out_5153713409265621922);
void car_h_28(double *state, double *unused, double *out_7604358550203645525);
void car_H_28(double *state, double *unused, double *out_71314392196091348);
void car_h_31(double *state, double *unused, double *out_3022644488244286851);
void car_H_31(double *state, double *unused, double *out_2242562314663426589);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}