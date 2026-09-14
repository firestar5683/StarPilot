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
void car_err_fun(double *nom_x, double *delta_x, double *out_2580454465484491227);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5942980338533536074);
void car_H_mod_fun(double *state, double *out_8194968061470735391);
void car_f_fun(double *state, double dt, double *out_4786356323138029797);
void car_F_fun(double *state, double dt, double *out_9135511833511698372);
void car_h_25(double *state, double *unused, double *out_8083637761377658508);
void car_H_25(double *state, double *unused, double *out_3291276236286070551);
void car_h_24(double *state, double *unused, double *out_6440652138727823346);
void car_H_24(double *state, double *unused, double *out_8160091101313777403);
void car_h_30(double *state, double *unused, double *out_5991949765328664151);
void car_H_30(double *state, double *unused, double *out_7818972566413678749);
void car_h_26(double *state, double *unused, double *out_8397464415311706259);
void car_H_26(double *state, double *unused, double *out_7032779555160126775);
void car_h_27(double *state, double *unused, double *out_1186756435998500064);
void car_H_27(double *state, double *unused, double *out_5595378495229735532);
void car_h_29(double *state, double *unused, double *out_4824205964252522414);
void car_H_29(double *state, double *unused, double *out_7308741222099286565);
void car_h_28(double *state, double *unused, double *out_936072129372815930);
void car_H_28(double *state, double *unused, double *out_5345110950533960314);
void car_h_31(double *state, double *unused, double *out_4090110893946851470);
void car_H_31(double *state, double *unused, double *out_7658987657393478251);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}