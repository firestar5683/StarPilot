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
void car_err_fun(double *nom_x, double *delta_x, double *out_3926092090457486519);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_1042755756890972147);
void car_H_mod_fun(double *state, double *out_6362512350679995207);
void car_f_fun(double *state, double dt, double *out_424859049759384026);
void car_F_fun(double *state, double dt, double *out_5354778108929478985);
void car_h_25(double *state, double *unused, double *out_2030817843873969747);
void car_H_25(double *state, double *unused, double *out_8509671287957375619);
void car_h_24(double *state, double *unused, double *out_6573865906285076625);
void car_H_24(double *state, double *unused, double *out_1855465829849189862);
void car_h_30(double *state, double *unused, double *out_8801653070224320683);
void car_H_30(double *state, double *unused, double *out_8639010235100615689);
void car_h_26(double *state, double *unused, double *out_7111205235488639723);
void car_H_26(double *state, double *unused, double *out_6195569466878119773);
void car_h_27(double *state, double *unused, double *out_3114072219241677790);
void car_H_27(double *state, double *unused, double *out_7632970526808511016);
void car_h_29(double *state, double *unused, double *out_3799979802563475038);
void car_H_29(double *state, double *unused, double *out_8128778890786223505);
void car_h_28(double *state, double *unused, double *out_2027345570885213463);
void car_H_28(double *state, double *unused, double *out_5235566165853797537);
void car_h_31(double *state, double *unused, double *out_5732447412946702694);
void car_H_31(double *state, double *unused, double *out_8479025326080415191);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}