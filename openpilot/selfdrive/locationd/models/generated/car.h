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
void car_err_fun(double *nom_x, double *delta_x, double *out_4327500179553376114);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3590090955330921238);
void car_H_mod_fun(double *state, double *out_2916657039326237022);
void car_f_fun(double *state, double dt, double *out_7982950417846647171);
void car_F_fun(double *state, double dt, double *out_1874021749855498275);
void car_h_25(double *state, double *unused, double *out_6775859317196018453);
void car_H_25(double *state, double *unused, double *out_6439637689315728699);
void car_h_24(double *state, double *unused, double *out_8888486471797321371);
void car_H_24(double *state, double *unused, double *out_1619316184659740436);
void car_h_30(double *state, double *unused, double *out_8976647325717484889);
void car_H_30(double *state, double *unused, double *out_6310298742172488629);
void car_h_26(double *state, double *unused, double *out_948533943747329952);
void car_H_26(double *state, double *unused, double *out_7096491753426040603);
void car_h_27(double *state, double *unused, double *out_4171453996387320802);
void car_H_27(double *state, double *unused, double *out_4135535430372063718);
void car_h_29(double *state, double *unused, double *out_4014267328036191657);
void car_H_29(double *state, double *unused, double *out_6820530086486880813);
void car_h_28(double *state, double *unused, double *out_8361259295207794082);
void car_H_28(double *state, double *unused, double *out_1738131069417350239);
void car_h_31(double *state, double *unused, double *out_1105413333558030732);
void car_H_31(double *state, double *unused, double *out_6470283651192689127);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}