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
void car_err_fun(double *nom_x, double *delta_x, double *out_8582732006986044846);
void car_inv_err_fun(double *nom_x, double *true_x, double *out_8739532987512141139);
void car_H_mod_fun(double *state, double *out_6103396635768963277);
void car_f_fun(double *state, double dt, double *out_1718122372243364932);
void car_F_fun(double *state, double dt, double *out_3952025267043728807);
void car_h_25(double *state, double *unused, double *out_7141069195581345731);
void car_H_25(double *state, double *unused, double *out_3089791590143273960);
void car_h_24(double *state, double *unused, double *out_7882213092182597875);
void car_H_24(double *state, double *unused, double *out_5262441189148773526);
void car_h_30(double *state, double *unused, double *out_8844017396137502869);
void car_H_30(double *state, double *unused, double *out_571458631636025333);
void car_h_26(double *state, double *unused, double *out_47707931871505729);
void car_H_26(double *state, double *unused, double *out_214734379617526641);
void car_h_27(double *state, double *unused, double *out_3085677766224822857);
void car_H_27(double *state, double *unused, double *out_2746221943436450244);
void car_h_29(double *state, double *unused, double *out_6605119900545468463);
void car_H_29(double *state, double *unused, double *out_61227287321633149);
void car_h_28(double *state, double *unused, double *out_8962024790070879613);
void car_H_28(double *state, double *unused, double *out_5143626304391163723);
void car_h_31(double *state, double *unused, double *out_6721943511569860764);
void car_H_31(double *state, double *unused, double *out_411473722615824835);
void car_predict(double *in_x, double *in_P, double *in_Q, double dt);
void car_set_mass(double x);
void car_set_rotational_inertia(double x);
void car_set_center_to_front(double x);
void car_set_center_to_rear(double x);
void car_set_stiffness_front(double x);
void car_set_stiffness_rear(double x);
}